# Roadmap

Built as a sequence of small, single-purpose PRs into `develop` — infrastructure and data model
before AI, AI before UI — rather than jumping straight from the skeleton to model training.

## Done

- [x] Repo scaffold, configs, DB models, API stubs, service stubs, Docker, tests (`v0.1.0` on `main`)
- [x] `feature/project-bootstrap` (`v0.2.0`) — `app/core/` lifecycle (startup/shutdown/exceptions/
      dependencies), `app/middleware/` (request ID, timing, request logging), `app/database/`
      split into `base.py`/`session.py`, `/` and `/health` routes. No AI yet — the goal was just:
      app starts, config loads, DB connects, Swagger loads.
- [x] `docs/python-version` — README prerequisites; `torch==2.4.1` has no wheels for Python 3.13+.
- [x] `feature/database` — Alembic wired up (`alembic/env.py` reads the DB URL from
      `app.config.settings`, not `alembic.ini`), one initial migration for `users`/`patients`/
      `studies`/`predictions`. No separate "history" table — `/history` is a query pattern over
      `predictions`/`studies`, not its own schema.
- [x] `feature/image-upload` — `POST /upload`: validate, save to disk, create `Patient`/`Study`,
      return `study_id`. No model involved.
- [x] `feature/preprocessing` — `app/preprocessing/transforms.py`: resize, RGB convert, ImageNet
      normalize, tensor conversion. No inference.
- [x] `feature/model-training` — ResNet-50 baseline (`app/models/resnet.py`), dataset loader
      (`datasets/chest_xray_dataset.py`, real `ChestXrayDataset` + `DummyChestXrayDataset` since no
      real dataset is downloaded yet), training loop (`training/train.py`), `PredictionService`,
      `GradCAMService`. Validated only against dummy/random data — diagnostic accuracy is
      unmeasured until real chest X-ray data is loaded via `--labels-csv`/`--image-dir`.
- [x] `feature/gradcam` — wired `PredictionService` + `GradCAMService` into `POST /predict/{study_id}`,
      persists a `Prediction` row. Model checkpoint loads lazily (app still boots without one;
      `/predict` returns `503` instead of crashing if no checkpoint is trained yet).
- [x] `feature/report-generator` — `ReportService` calls the LLM configured in `config.yaml`
      (default `gpt-4o-mini`) to turn findings into a narrative report. Failure (no `LLM_API_KEY`,
      bad key, API error) is caught and logged — `report_text` stays `null`, request still succeeds.
- [x] `feature/frontend` — Streamlit UI (`frontend/app.py`): upload → predict → probability chart +
      Grad-CAM overlay + report text. Backend now also serves `/storage/*` as static files so a
      frontend on a different host can fetch generated images.
- [x] `feature/deployment` — production `Dockerfile` (Gunicorn + Uvicorn workers, runs
      `alembic upgrade head` on boot), `frontend` service added to `docker-compose.yml`, GitHub
      Actions CI (`pytest` on every push/PR to `main`/`develop`).
- [x] `docs/roadmap-update` — this file.
- [x] `feature/history` — implemented `GET /history/{patient_id}`, ordered by `id` (not
      `created_at` — SQLite's `CURRENT_TIMESTAMP` only has second resolution, which sorted
      same-second predictions ambiguously).
- [x] Postgres added to `docker-compose.yml` (`db` service) for dev/prod parity — SQLite remains
      the zero-setup default when running `uvicorn` directly, outside Docker.
- [x] `v1.0.0` tagged on `main`.
- [x] `feature/real-data` — `scripts/download_sample_data.py` pulls a genuine NIH ChestX-ray14
      subset (300 real images + labels, via a public no-auth-required HF mirror) into
      `datasets/chestxray14/`. `training/train.py` run against it for real: val AUC climbed
      0.57 → 0.70 over 3 epochs, confirming the full pipeline (loader → transforms → ResNet-50 →
      checkpoint → `PredictionService` → `GradCAMService`) works end-to-end on authentic data, not
      just `DummyChestXrayDataset`.
- [x] `v1.1.0` tagged on `main`.
- [x] `docs/system-design` — `docs/system-design.md`, `docs/database.md`, `docs/model.md`,
      `docs/deployment.md`, `docs/known-limitations.md`, plus real SVG diagrams
      (`docs/images/`: architecture, sequence, component, deployment, ER).
- [x] `docs/project-report` — `docs/project-report.md` (+ PDF export), a standalone hiring-manager
      -facing report referencing the diagrams already built rather than duplicating them.
- [x] `feature/model-improvements` — scaled the real dataset 300 → 2,000 images; added per-class
      `pos_weight` (class-imbalance correction), a `CosineAnnealingLR` scheduler, best-epoch
      checkpoint selection (previously the *last* epoch was always saved, even when it was worse
      than an earlier one — see `model.md`'s overfitting section), and a fixed random seed for
      reproducibility (two unseeded runs of the same config had produced val AUC 0.71 and 0.66).
      Also discovered `DEVICE=mps` works for GPU training on Apple Silicon — ~5x faster per epoch
      than CPU. A code review then caught a real, pre-existing bug: training augmentation was
      never actually applied (a shared-dataset-object mutation silently left both train and val
      using the eval transform since the codebase's first preprocessing implementation) — fixed by
      building two separate dataset instances instead. Best val AUC observed (seeded, post-fix):
      **0.71** (epoch 4 of 10), with visibly gentler overfitting than the pre-fix runs.

## Known gaps (worth tracking)

- Only ~2,000 real images have been used — a real step up from 300, but still nowhere near enough
  for a clinically meaningful model. The AUC ≥ 0.90 target is still unmet (best observed: 0.71),
  and the model overfits within ~3-5 epochs at this scale — see `model.md`. Scaling to the full
  ~112k-image dataset, plus explicit early stopping, is real future work, not a formality.
- No auth (JWT/OAuth2) on patient-data endpoints yet.
- No per-inference audit logging beyond the request-logging middleware.
- No live public deployment — runs locally / via `docker-compose` only.

## Branch Flow

```
main --(v0.1.0)--> develop --> <branch> --> PR --> develop --> ... --> main (v1.0.0)
```
Each branch is reviewed via its own PR before merging — including one-line doc fixes.
