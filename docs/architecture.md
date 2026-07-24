# Architecture

This is the 10-minute overview. For the reasoning behind each choice, see
[system-design.md](system-design.md). For deep dives: [database.md](database.md),
[model.md](model.md), [api.md](api.md), [deployment.md](deployment.md),
[known-limitations.md](known-limitations.md).

## Pipeline

![Architecture diagram](images/architecture.svg)

```
User -> Streamlit Frontend -> FastAPI -> Inference Pipeline -> ResNet-50 (CNN)
      -> Grad-CAM -> LLM Report -> Postgres/SQLite -> API Response -> Frontend
```

This is a real, wired pipeline, not an aspiration — see [api.md](api.md) for exact request/response
shapes and [sequence-predict.svg](images/sequence-predict.svg) for the full call sequence.

## Why each component exists

| Component | Why |
|---|---|
| **Streamlit frontend** | Fastest path to a usable clinician-facing UI on top of a Python ML stack — no separate JS build, no API client to hand-write. Trade-off discussed in [system-design.md](system-design.md). |
| **FastAPI** | Async, Pydantic-validated request/response models, auto-generated OpenAPI docs (`/docs`) for free — matters for an API a frontend and reviewers both need to inspect. Why not Flask: see [system-design.md](system-design.md). |
| **`app/core/` + `app/middleware/`** | App lifecycle (startup DB check, shutdown) and cross-cutting concerns (request ID, timing, structured logging) kept out of route handlers, so routes stay thin. |
| **Service layer (`app/services/`)** | Routes never touch `torch`/`PIL`/SQL directly — each concern (validate, preprocess, predict, explain, report, store) is one class, independently testable and independently swappable. |
| **ResNet-50** | Well-understood, ImageNet-pretrained baseline with strong prior results on chest X-ray multi-label classification — appropriate for a project that had to ship a working pipeline over an accuracy leaderboard win. See [model.md](model.md) for the training details and honest accuracy caveat. |
| **Grad-CAM** | Post-hoc, model-architecture-preserving explainability — no retraining, no changing the model to get localization. Matters for a clinician-facing tool where "why did the model say this" is not optional. |
| **LLM report generation** | Turns 14 raw probabilities into the narrative format radiology reports actually use, without hand-writing a template engine. Designed to degrade gracefully (see below) rather than block a diagnosis on an LLM being available. |
| **Postgres (prod) / SQLite (dev+test)** | Postgres for real concurrent access and production durability; SQLite by default locally so `pip install && run` has zero external setup. Schema is identical either way (SQLAlchemy + Alembic). |
| **Alembic** | Schema changes are reviewable, reversible migrations, not implicit `create_all()` calls that silently diverge between environments. |

## Design decisions worth knowing about

- **`/upload` and `/predict/{study_id}` are separate endpoints.** Uploading and running inference
  are different concerns with different failure modes (a bad file vs. no trained model) and
  different costs (cheap vs. a GPU/CPU-bound forward pass). Splitting them means a study can be
  re-predicted (e.g. after a model update) without re-uploading the image.
- **No dedicated "history" table.** `GET /history/{patient_id}` is a join query over
  `predictions`/`studies`, not its own schema — see [database.md](database.md) for why that's a
  deliberate choice, not an oversight.
- **The AI services degrade gracefully, not fatally.** No trained checkpoint yet → `/predict`
  returns `503`, not a crash. No `LLM_API_KEY` configured → `report_text` is `null`, the rest of
  the response still succeeds. This matters more in a medical-imaging tool than in a typical CRUD
  app: a missing report should never hide a diagnosis that was already computed.

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
    inference/      Old pipeline scaffolding, superseded by routes calling services directly
    preprocessing/  Image preprocessing utilities
    explainability/ Reserved (Grad-CAM currently lives in app/services/gradcam_service.py)
    reports/        Reserved (LLM report logic currently lives in app/services/report_service.py)
    auth/           Reserved — no auth implemented yet, see known-limitations.md
    utils/          Shared helpers
    schemas/        Pydantic request/response models
    config/         Settings, logging, config.yaml, constants
  alembic/          DB migrations
  training/         Training scripts, checkpoints
  datasets/         Dataset loaders (data itself is gitignored)
  scripts/          Utility scripts (e.g. download_sample_data.py)
  notebooks/        Exploration notebooks
  frontend/         Streamlit UI
  tests/            Pytest suite
  docs/             Documentation (this directory)
  deployment/       Deployment configs (CI/CD, cloud)
```
