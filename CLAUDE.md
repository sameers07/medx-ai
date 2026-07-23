# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

MedX AI is an end-to-end medical imaging AI platform (chest X-ray disease prediction, Grad-CAM
explainability, LLM-generated radiology reports), built on a 2-day timeline. `ImageService`,
`PredictionService`, and `GradCAMService` are implemented (Day 1); `ReportService` is still a
`NotImplementedError` stub (Day 2), and the API routes / `run_pipeline()` don't call the services
yet — that wiring is also Day 2. See `docs/roadmap.md` for the day-by-day plan before assuming a
feature works end-to-end; a service having real logic does not mean a route calls it yet.

**No real dataset is downloaded in this repo.** Model/Grad-CAM code is validated against
`DummyChestXrayDataset` (random tensors, `datasets/chest_xray_dataset.py`) — diagnostic accuracy
is unmeasured. Point `training/train.py` at `--labels-csv`/`--image-dir` once real chest X-ray data
(MIMIC-CXR/CheXpert require credentialed access; ChestX-ray14 is open) is available locally.

## Commands

```bash
# Setup — use Python 3.11 (matches Dockerfile); torch==2.4.1 has no wheels for 3.13+
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run the API (http://localhost:8000, docs at /docs)
uvicorn app.api.main:app --reload

# Run via Docker
docker-compose up

# Tests
pytest                      # whole suite (config: pytest.ini, tests/ only, test_*.py)
pytest tests/test_api.py    # single file
pytest tests/test_api.py::test_health   # single test
```

There is no lint/format/typecheck tooling configured yet (no ruff/black/mypy config in the repo).

## Architecture

### Pipeline (the core mental model)

Every feature maps onto one linear pipeline, defined conceptually in `docs/architecture.md` and
skeletonized stage-by-stage in [app/inference/pipeline.py](app/inference/pipeline.py):

```
Image Upload -> Validation -> Preprocessing -> Prediction (CNN/ViT) -> Explainability (Grad-CAM)
             -> LLM Report Generation -> Database (Postgres) -> API Response
```

`run_pipeline()` in that file orchestrates the stages by calling into the corresponding service
classes. When wiring up a stage, implement it in its service class first, then update the matching
no-op function in `pipeline.py` to call it — don't put business logic directly in the pipeline
functions or in the API route handlers.

### Layering

- `app/api/routes/` — FastAPI routers only. Thin: parse request, call a service/pipeline, return
  response. Still returning `{"message": "Coming Soon"}` stubs — no business logic wired in yet.
- `app/services/` — one class per concern:
  - `ImageService` — validation + preprocessing (implemented)
  - `PredictionService` — loads a checkpoint via `app/models/resnet.py`, returns
    `{class_name: probability}` (implemented)
  - `GradCAMService` — Grad-CAM overlay via `pytorch_grad_cam`, targets `layer4` (implemented)
  - `StorageService` — local filesystem save/load under `settings.storage_dir` (implemented)
  - `ReportService` — LLM narrative report generation (still `NotImplementedError`)
- `app/inference/pipeline.py` — still no-op stage functions; wiring them to call the services
  above is Day 2 work, not done yet.
- `app/models/resnet.py` — `build_model(num_classes, pretrained)`: ResNet-50 baseline, final `fc`
  replaced for multi-label output (pair with `BCEWithLogitsLoss` / sigmoid, not softmax).
- `app/preprocessing/transforms.py` — `get_transforms(train: bool)`, sized/normalized from
  `config.yaml` (ImageNet mean/std, since the backbone is ImageNet-pretrained).
- `app/config/model_config.py` — loads `config.yaml` once into a module-level `config` dict;
  import `config` from here rather than re-reading the YAML.
- `datasets/chest_xray_dataset.py` — `ChestXrayDataset` (real data: labels CSV + image dir, one
  0/1 column per `config.yaml`'s `model.class_names`) and `DummyChestXrayDataset` (random
  data, used because no real dataset is downloaded yet). Note: `.gitignore` blocks everything
  under `datasets/` except `README.md` and `*.py` — that's intentional, so loader code is tracked
  but dataset files never are.
- `training/train.py` — training loop wired to `config.yaml` (batch size/epochs/lr/optimizer),
  computes per-label + averaged AUC, saves to `settings.model_weights_path`. Defaults to
  `DummyChestXrayDataset`; pass `--labels-csv`/`--image-dir` for real data.
- `app/database/` — SQLAlchemy models (`patient_model.py`, `prediction_model.py`, `user_model.py`)
  and `connection.py` (engine/session/`Base`/`get_db` dependency). Models are schema-only, no query
  logic — that belongs in services.
- `app/config/` — `settings.py` (pydantic-settings, reads `.env`), `config.yaml` (model/training/
  explainability/report-generation hyperparameters, not secrets), `logging.py`.
- `app/auth/`, `app/explainability/`, `app/reports/`, `app/schemas/`, `app/utils/` — currently
  empty packages reserved for future work.
- `notebooks/`, `frontend/`, `scripts/`, `deployment/` — top-level dirs are placeholders (READMEs
  only so far).

### Data model

`Patient` 1—N `Study` (an uploaded image/scan) 1—N `Prediction` (disease label probabilities as
JSON, path to the Grad-CAM heatmap, generated report text). `Prediction` also optionally links to
`User` (the clinician). See `app/database/*_model.py`.

### Config vs. settings

Two separate config surfaces — don't conflate them:
- `app/config/settings.py` / `.env` — runtime/deployment config (DB URL, secrets, API keys, device).
- `app/config/config.yaml` — ML/product config (model architecture, training hyperparameters,
  Grad-CAM target layer, LLM report provider/model/max_tokens).

## Branching

`main` (stable releases) <- `develop` <- `feature/*`. Branch from `develop`, PR back into `develop`;
`main` only receives merges from a stable `develop`. Run `pytest` before pushing. See
`docs/contributing.md`.
