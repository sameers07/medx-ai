FROM python:3.11-slim

WORKDIR /app

# libgl1/libglib2.0-0: opencv-python (pulled in by grad-cam) needs libGL.so.1 at import time,
# which python:3.11-slim doesn't ship — omitting this makes the container crash-loop on boot.
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Apply pending migrations, then serve with Gunicorn's Uvicorn workers (not --reload — that's
# for local dev via `uvicorn app.api.main:app --reload`, see README).
CMD ["sh", "-c", "alembic upgrade head && gunicorn app.api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"]
