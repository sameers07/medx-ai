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
    services/       Business logic (prediction, report, gradcam, image, storage)
    database/       ORM models + connection
    models/         Model architecture definitions
    inference/       Pipeline orchestration
    preprocessing/  Image preprocessing utilities
    explainability/ Grad-CAM implementation
    reports/        LLM prompt templates / report formatting
    auth/           Auth (JWT/OAuth2)
    utils/          Shared helpers
    schemas/        Pydantic request/response models
    config/         Settings, logging, config.yaml
  training/         Training scripts, checkpoints
  datasets/         Dataset loaders (data itself is gitignored)
  notebooks/        Exploration notebooks
  frontend/         Streamlit UI
  tests/            Pytest suite
  docs/             Documentation
  scripts/          Utility scripts
  deployment/       Deployment configs (CI/CD, cloud)
```
