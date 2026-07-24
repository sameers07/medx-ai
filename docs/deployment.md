# Deployment

![Deployment diagram](images/deployment-diagram.svg)

```
Browser -> docker-compose -> FastAPI (api container) -> PostgreSQL (db container)
                          -> Streamlit (frontend container)
```

## `docker-compose.yml` — three services

- **`db`** — `postgres:16-alpine`, with a healthcheck (`pg_isready`). `api` waits for `db` to
  report healthy (`depends_on: condition: service_healthy`) before starting, so migrations never
  race a not-yet-ready database.
- **`api`** — built from the repo's `Dockerfile`, served by **Gunicorn with Uvicorn worker
  processes** (`--workers 4 --worker-class uvicorn.workers.UvicornWorker`), not `uvicorn --reload`
  (that's the local-dev-only path). Runs `alembic upgrade head` before starting the server —
  `sh -c "alembic upgrade head && gunicorn ..."` in the `Dockerfile`'s `CMD`.
- **`frontend`** — same image, different command (`streamlit run frontend/app.py`).
  `BACKEND_URL=http://api:8000` overrides the frontend's default `localhost:8000`, so it reaches
  `api` over the Docker network by service name.

`api` and `frontend` both bind-mount the repo root (`.:/app`), which is also how `storage/`
(uploads + Grad-CAM heatmaps) and `training/checkpoints/` (model weights) end up shared between
containers and the host, rather than baked into the image or lost on container recreation.

Running `uvicorn` directly, outside Docker, still defaults to SQLite (see
[system-design.md](system-design.md)) — Postgres is only used when going through `docker-compose`.

## Dockerfile

```bash
FROM python:3.11-slim
RUN apt-get install -y libgl1 libglib2.0-0   # see "real bugs" below
RUN pip install -r requirements.txt
CMD ["sh", "-c", "alembic upgrade head && gunicorn app.api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"]
```

`.dockerignore` keeps `venv/`, `.git/`, `storage/`, test data, and `__pycache__` out of the build
context.

## CI

`.github/workflows/ci.yml` — GitHub Actions, `ubuntu-latest`, Python 3.11 (`cache: pip`), installs
`requirements.txt`, runs `pytest`. Triggers on push/PR to `main` and `develop`. This runs the test
suite only (against the default SQLite path) — it does not build or run the Docker images.

## Real bugs hit deploying this, not hypothetical ones

- **`opencv-python` (pulled in transitively by `grad-cam`) needs `libGL.so.1`**, which
  `python:3.11-slim` doesn't ship. Without `libgl1`/`libglib2.0-0` installed, the container
  crash-loops on boot with `ImportError: libGL.so.1: cannot open shared object file` — only found
  by actually running the built image, not by any unit test.
- **`docker-compose.yml`'s `version: "3.9"` key is obsolete** in current Compose and warns on
  every command — removed.
- **A stale local `medx.db` file, bind-mounted into the container, caused `alembic upgrade head`
  to fail with "table already exists"** during manual verification — not a code bug, but a real
  reminder that the bind-mounted SQLite dev DB and the containerized Postgres DB are easy to
  confuse if you don't clean up between runs.

## Production notes

- `SECRET_KEY`, `LLM_API_KEY`, and `DATABASE_URL` must be set for real use — `.env.example`'s
  values are dev-only placeholders.
- Gunicorn's worker count (4) is hardcoded in the `Dockerfile` — should scale with available CPU,
  not stay fixed.
- No TLS/HTTPS termination is configured anywhere in this repo — a real deployment would need a
  reverse proxy (nginx, Caddy, or a cloud load balancer) in front of `api`.
