# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

MedX AI is an end-to-end medical imaging AI platform: chest X-ray upload, ResNet-50 disease
prediction, Grad-CAM explainability, LLM-generated radiology reports, and a Streamlit frontend —
all wired end-to-end (`v1.1.0` on `main`). See `docs/roadmap.md` for the full build history (built
as a sequence of single-purpose PRs: bootstrap → database → upload → preprocessing → model →
Grad-CAM → reports → frontend → deployment → history → docs → model improvements) and its
"Known gaps" section for what's still genuinely missing (auth, audit logging, real-scale training
data).

**Training data:** `scripts/download_sample_data.py` pulls a small (~2,000 image) but genuine NIH
ChestX-ray14 subset from a public, no-auth-required Hugging Face mirror into
`datasets/chestxray14/`. `DummyChestXrayDataset` (random tensors) still exists for quick pipeline
smoke-testing without a network call. Best val AUC observed so far: 0.71 (epoch 4 of 10, `--seed
42`) — the model reproducibly overfits within ~3-5 epochs at this scale, which is why
`training/train.py` now saves the best epoch by val AUC rather than just the last one, fixes a
random seed (unseeded runs of the same config varied 0.71 vs 0.66), and — important — no longer
has the pre-existing bug where `random_split`'s shared `Subset.dataset` reference meant setting
`.transform` for val silently overwrote it for train too, so augmentation was never actually
applied until this branch. `DEVICE=mps` works for GPU training on Apple Silicon (~5x faster/epoch
than CPU); no CUDA GPU in this environment. Nowhere near the documented AUC ≥ 0.90 target or a
clinically meaningful model — don't cite these numbers as if they mean anything beyond "the
pipeline demonstrably learns."

## Commands

```bash
# Setup — use Python 3.11 (matches Dockerfile); torch==2.4.1 has no wheels for 3.13+
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the API (http://localhost:8000, docs at /docs) — apply migrations first
alembic upgrade head
uvicorn app.api.main:app --reload

# Get real training data, then train
python -m scripts.download_sample_data --n 2000 --split train
python -m training.train --labels-csv datasets/chestxray14/labels.csv --image-dir datasets/chestxray14

# Full stack, containerized (API + Streamlit frontend + Postgres)
docker-compose up --build

# Tests
pytest                            # whole suite (config: pytest.ini, tests/ only, test_*.py)
pytest tests/test_predict.py      # single file
pytest tests/test_predict.py::test_predict_404_for_missing_study   # single test
```

There is no lint/format/typecheck tooling configured yet (no ruff/black/mypy config in the repo).

## Architecture

### Pipeline (the core mental model)

```
Image Upload -> Validation -> Preprocessing -> Prediction (ResNet-50) -> Explainability (Grad-CAM)
             -> LLM Report Generation -> Database (Postgres/SQLite) -> API Response
```

This is fully wired, not conceptual: `POST /upload` does validation + storage, `POST
/predict/{study_id}` does preprocessing → prediction → Grad-CAM → report generation → DB persist,
`GET /history/{patient_id}` reads it back. `app/inference/pipeline.py` is old scaffolding from
before the routes were wired directly — nothing currently calls into it; don't assume it runs.

### Layering

- `app/api/routes/` — FastAPI routers, thin: parse request, call services/DB, return response.
  - `root.py`, `health.py` — liveness.
  - `upload.py` — `POST /upload`: validate, save to disk, get-or-create `Patient`, create `Study`.
  - `predict.py` — `POST /predict/{study_id}`: runs `PredictionService` → `GradCAMService` →
    `ReportService`, persists a `Prediction` row. Model/report services load lazily and are
    cached (`@lru_cache`) so the app boots fine with no trained checkpoint or `LLM_API_KEY` —
    `/predict` returns `503` without a checkpoint; report failures just leave `report_text: null`.
  - `history.py` — `GET /history/{patient_id}`: `patient_id` is the *external* ID (same value
    passed to `/upload`), not the internal DB row id. Ordered by `Prediction.id` descending, not
    `created_at` — SQLite's `CURRENT_TIMESTAMP` only has second resolution.
- `app/services/` — all implemented: `ImageService` (validate + preprocess), `PredictionService`
  (loads a checkpoint via `app/models/resnet.py`), `GradCAMService` (`pytorch_grad_cam`, targets
  `layer4`), `ReportService` (calls the LLM in `config.yaml`'s `report_generation` block),
  `StorageService` (local filesystem under `settings.storage_dir`).
- `app/models/resnet.py` — `build_model(num_classes, pretrained)`: ResNet-50, final `fc` replaced
  for multi-label output (pair with `BCEWithLogitsLoss` / sigmoid, not softmax).
- `app/preprocessing/transforms.py` — `get_transforms(train: bool)`, sized/normalized from
  `config.yaml` (ImageNet mean/std, since the backbone is ImageNet-pretrained).
- `app/config/model_config.py` — loads `config.yaml` once into a module-level `config` dict;
  import `config` from here rather than re-reading the YAML.
- `datasets/chest_xray_dataset.py` — `ChestXrayDataset` (real data: labels CSV + image dir, one
  0/1 column per `config.yaml`'s `model.class_names`) and `DummyChestXrayDataset`. `.gitignore`
  blocks everything under `datasets/` except `README.md` and `*.py` — loader code is tracked,
  dataset files never are.
- `scripts/download_sample_data.py` — fetches real NIH ChestX-ray14 images via HF's
  datasets-server "rows" API (no full-parquet download, no auth). Don't `pip install` the HF
  `datasets` package for this — it shadows this repo's own top-level `datasets/` package and
  breaks every import of it (hit this once; `requests` alone is enough for the script).
- `training/train.py` — training loop wired to `config.yaml` (batch size/epochs/lr/optimizer),
  computes per-label + averaged AUC, saves to `settings.model_weights_path`. Defaults to
  `DummyChestXrayDataset`; pass `--labels-csv`/`--image-dir` for real data.
- `app/database/` — `base.py` (`Base`), `session.py` (`engine`/`SessionLocal`/`get_db`),
  `connection.py` (back-compat facade re-exporting both). `patient_model.py` (`Patient`, `Study`),
  `prediction_model.py` (`Prediction`), `user_model.py` (`User`) — schema-only, no query logic.
  Importing `app.database` (the package `__init__.py`) registers all three model modules on the
  mapper registry — necessary because `Prediction.user = relationship("User")` is a string
  reference that SQLAlchemy can't resolve unless `User` has been imported *somewhere*; hit this as
  a real `KeyError: 'User'` in production once before centralizing the imports there.
- `alembic/` — schema is Alembic-owned, not `Base.metadata.create_all()`. `env.py` reads the DB
  URL from `app.config.settings`, not `alembic.ini`. Run `alembic upgrade head` before anything
  that touches the DB — a fresh DB has no tables otherwise.
- `app/core/` — `startup.py`/`shutdown.py` (lifespan, DB connectivity check), `exceptions.py`
  (handlers), `dependencies.py` (`get_db`, `get_settings`).
- `app/middleware/` — `request_id.py`, `timing.py`, `logging.py`. Added in that call order in
  `main.py` deliberately: Starlette wraps outer-to-inner in *reverse* of `add_middleware()` call
  order, so RequestID (added last) runs first and sets `request.state.request_id` before Logging
  reads it. Don't reorder those calls without re-checking that dependency.
- `app/config/` — `settings.py` (pydantic-settings, reads `.env`), `config.yaml` (model/training/
  explainability/report-generation hyperparameters, not secrets), `constants.py`, `logging.py`.
- `frontend/app.py` — Streamlit: upload → predict → probability chart + Grad-CAM image + report.
  `BACKEND_URL` env var overrides the default `localhost:8000` (set to `http://api:8000` in
  `docker-compose.yml`). The Grad-CAM image is fetched from the backend's `/storage/*` static
  mount, not read off local disk — matters if frontend and backend ever run on different hosts.
- `app/auth/`, `app/explainability/`, `app/reports/` — still empty, reserved for future work
  (auth is a known gap — see `docs/roadmap.md`).

### Data model

`Patient` 1—N `Study` (an uploaded image) 1—N `Prediction` (disease label probabilities as JSON,
Grad-CAM heatmap path, generated report text). `Prediction` also optionally links to `User`. See
`app/database/*_model.py`.

### Config vs. settings

Two separate config surfaces — don't conflate them:
- `app/config/settings.py` / `.env` — runtime/deployment config (DB URL, secrets, API keys, device).
- `app/config/config.yaml` — ML/product config (model architecture, training hyperparameters,
  Grad-CAM target layer, LLM report provider/model/max_tokens).

### Deployment

`docker-compose.yml` runs three services: `db` (Postgres 16, healthchecked), `api` (Gunicorn +
Uvicorn workers, runs `alembic upgrade head` on boot), `frontend` (Streamlit). Running `uvicorn`
directly (no Docker) defaults to SQLite — Postgres is only used through compose. The `Dockerfile`
installs `libgl1`/`libglib2.0-0` — `opencv-python` (pulled in by `grad-cam`) needs `libGL.so.1`,
which `python:3.11-slim` doesn't ship; omitting it crash-loops the container on boot.

## Branching

`main` (stable releases) <- `develop` <- `feature/*`/`docs/*`. Branch from `develop`, PR back into
`develop` — every change goes through a PR and review, including one-line doc fixes; `main` only
receives merges from a stable `develop`. Run `pytest` before pushing. See `docs/contributing.md`.
