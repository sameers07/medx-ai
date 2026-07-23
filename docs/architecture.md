# Architecture

```
Image Upload
    |
Validation
    |
Preprocessing
    |
Prediction (CNN/ViT)
    |
Explainability (Grad-CAM)
    |
LLM Report Generation
    |
Database (Postgres)
    |
API Response
```

## Folder Structure

```
medx-ai/
  app/
    api/            REST endpoints (FastAPI)
    core/           App lifecycle: startup, shutdown, exception handlers, shared dependencies
    middleware/     Request ID, timing, request logging
    services/       Business logic (prediction, report, gradcam, image, storage)
    database/       ORM models, base/session/connection
    models/         Model architecture definitions
    inference/       Pipeline orchestration
    preprocessing/  Image preprocessing utilities
    explainability/ Grad-CAM implementation
    reports/        LLM prompt templates / report formatting
    auth/           Auth (JWT/OAuth2)
    utils/          Shared helpers
    schemas/        Pydantic request/response models
    config/         Settings, logging, config.yaml, constants
  alembic/          DB migrations (see Database section below)
  training/         Training scripts, checkpoints
  datasets/         Dataset loaders (data itself is gitignored)
  notebooks/        Exploration notebooks
  frontend/         Streamlit UI
  tests/            Pytest suite
  docs/             Documentation
  scripts/          Utility scripts
  deployment/       Deployment configs (CI/CD, cloud)
```

## Database

Tables: `users`, `patients`, `studies`, `predictions` (see `app/database/*_model.py`). There is no
separate "history" table — `GET /history/{patient_id}` is served by querying `predictions` joined
through `studies`, so history is a read pattern on existing data, not its own schema.

Schema changes go through Alembic, not `Base.metadata.create_all()`:
```bash
alembic upgrade head                                    # apply migrations
alembic revision --autogenerate -m "add X to Y"          # after changing a model
```
`alembic/env.py` reads the DB URL from `app.config.settings` (i.e. `.env`), not from
`alembic.ini` — don't hardcode a connection string there.

## Model & Data

- Datasets: MIMIC-CXR / ChestX-ray14 / CheXpert (chest X-rays, gitignored — see `datasets/README.md`).
- Baseline model: ResNet-50, transfer learning from ImageNet (`app/config/config.yaml`).
- Target: AUC ≥ 0.90 on held-out multi-label classification (14 conditions).

## Explainability

Grad-CAM on the model's final conv block (`layer4`), with Grad-CAM++ as a fallback for finer
localization. Heatmaps are validated by visual sanity check (highlighted regions should align with
plausible pathology, e.g. opacities for pneumonia) rather than automated metrics.

## LLM Report Generation

Findings (disease labels + probabilities) are turned into a narrative report via the LLM
configured in `config.yaml` (`report_generation` block; default OpenAI `gpt-4o-mini`). Report
quality is judged by manual clinical-plausibility review, not automated text-similarity metrics.

## Auth, Logging, Deployment

- Auth: JWT/OAuth2 on endpoints that handle patient data (`app/auth/`).
- Logging: every inference (input, output, user, timestamp) should be auditable.
- Deployment: Dockerized FastAPI app served by Uvicorn/Gunicorn with multiple workers; Docker
  Compose for local multi-service runs (see `docker-compose.yml`).
