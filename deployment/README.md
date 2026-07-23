# deployment

## Docker Compose (recommended)

```bash
cp .env.example .env   # fill in LLM_API_KEY etc.
docker-compose up --build
```

Starts two services:
- `api` — FastAPI, served by Gunicorn with Uvicorn workers (`Dockerfile`). Runs
  `alembic upgrade head` on container start before serving.
- `frontend` — Streamlit, pointed at `api` over the Docker network (`BACKEND_URL=http://api:8000`).

## CI

`.github/workflows/ci.yml` runs the test suite on every push/PR to `main` and `develop`.

## Production notes

- `SECRET_KEY`, `LLM_API_KEY`, and `DATABASE_URL` must be set for real use — the defaults in
  `.env.example` are dev-only placeholders.
- `DATABASE_URL` should point at Postgres in production, not the default SQLite file.
- Gunicorn worker count is hardcoded to 4 in the `Dockerfile` — adjust for available CPU.
- The `storage/` directory (uploads, Grad-CAM heatmaps) and `training/checkpoints/` (model
  weights) are bind-mounted via `.:/app` in `docker-compose.yml`, not baked into the image.
