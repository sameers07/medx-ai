# System Design

The questions a reviewer is likely to ask, answered before they're asked.

## Why this architecture (layered, pipeline-shaped)?

The problem itself is a pipeline (upload → validate → preprocess → predict → explain → report →
persist), so the code is organized the same way: one service class per stage
(`app/services/*_service.py`), each independently testable, each callable from a route without the
route knowing anything about torch, PIL, or SQL. The alternative — putting model-loading and
image-processing logic directly in route handlers — would work for a demo but makes every stage
untestable in isolation and impossible to swap (e.g. a different model backbone, a different LLM
provider) without touching HTTP-handling code.

The project was also *built* in that pipeline order — infrastructure and data model before any AI
code — rather than jumping straight to model training. See [roadmap.md](roadmap.md) for the actual
branch sequence. That ordering was a deliberate choice, not just a nice-to-have: a bootstrap sprint
that proves "the app starts, config loads, DB connects, Swagger loads" is a much cheaper place to
catch structural mistakes than after training code, API routes, and a frontend are all already
built on top of a bad foundation.

## Why FastAPI instead of Flask?

- **Async by default** — a chest X-ray inference request involves file I/O, DB I/O, and a
  (currently synchronous, CPU-bound) model forward pass; FastAPI's async request handling means
  the I/O-bound parts (DB queries, LLM calls) don't block the event loop the way they would need
  extra tooling (Flask-async, gevent) to avoid in Flask.
- **Pydantic request/response models** (`app/schemas/*.py`) give free request validation and a
  guaranteed response shape — no manual `request.json()` parsing and no hand-written response
  serialization.
- **Automatic OpenAPI/Swagger (`/docs`)** — for a project that needs to be reviewed and understood
  quickly (by a frontend developer, by a reviewer, by a future engineer), a live, always-in-sync
  API reference that costs nothing to maintain is a real advantage over Flask, where it's a
  separate library and a separate thing that can drift from the code.
- Flask is arguably simpler for a single-file toy app, but this project has multiple routers,
  typed request/response contracts, and a dependency-injected DB session (`Depends(get_db)`) —
  exactly what FastAPI's dependency-injection system is for.

## Why ResNet-50?

- **Transfer learning from ImageNet** gives a strong feature extractor for free — training a CNN
  from scratch on a few hundred to a few thousand chest X-rays (see [model.md](model.md)) would
  not converge to anything useful; fine-tuning an ImageNet-pretrained backbone does.
  `pretrained=True` in `app/models/resnet.py` / `config.yaml` is not a default left unexamined —
  it's the reason the model learns anything at all from a small dataset.
- **Established baseline for this exact task.** Multi-label chest X-ray classification (ChestX-ray14
  and its variants) has a large body of published work using ResNet-50 as the baseline
  architecture — using the same baseline makes results comparable and the design defensible, as
  opposed to picking an exotic architecture with no track record on this problem.
- **Compute/complexity trade-off.** A ViT or a larger CNN would need more data and more compute to
  out-perform a fine-tuned ResNet-50 at this scale (this project trains on CPU in this
  environment) — not a reasonable trade for a project on this timeline. Nothing in the code
  prevents swapping `build_model()`'s backbone later; `config.yaml`'s `model.architecture` field
  exists for exactly that.

## Why Grad-CAM?

- **Doesn't require changing the model.** Grad-CAM computes class-discriminative localization from
  gradients flowing into the last convolutional block (`layer4`, per `config.yaml`) of the
  *already-trained* model — no architecture change, no retraining, no extra prediction head.
  Attention-based / inherently-interpretable architectures would require redesigning the model
  itself for a marginal interpretability gain.
- **Standard in medical imaging XAI.** Grad-CAM (and Grad-CAM++, noted as a fallback in
  `docs/architecture.md`'s history) is the most widely used post-hoc CNN explainability method in
  published radiology-AI work, which matters for a tool whose explanations need to be
  understandable to clinicians, not just ML engineers.
- **Honest caveat:** a heatmap is not a diagnosis and hasn't been clinically validated here — see
  [known-limitations.md](known-limitations.md).

## Why PostgreSQL (and SQLite by default)?

- Postgres is the production target: ACID-compliant, handles concurrent writes from multiple
  Gunicorn workers correctly (SQLite's file-level locking does not), and is what the `docker-compose
  db` service actually runs.
- SQLite is the **local/test default** purely for zero-setup developer experience and fast,
  isolated tests (every test spins up its own throwaway SQLite file — no shared test DB, no
  cross-test pollution, no external service needed in CI). The schema is identical either way —
  SQLAlchemy + Alembic are DB-agnostic here, with one `connect_args` check in
  `app/database/session.py` for SQLite's threading quirk being the only DB-specific line in the
  codebase. Switching is `DATABASE_URL=postgresql://...` in `.env`; nothing else changes.

## Why split `/upload` from `/predict/{study_id}`?

Two different concerns with two different failure modes and costs: uploading is cheap and mostly
about file I/O and validation; predicting is a CPU/GPU-bound model forward pass that can fail in
its own way (no trained checkpoint → `503`). Separating them means a study can be re-predicted
(e.g. after training a better model) without re-uploading the image, and it means the upload path
never needs to know anything about the model.

## How would this scale to multiple models?

Not implemented today — this is a real, acknowledged gap (see
[known-limitations.md](known-limitations.md)) — but the shape of the fix:

1. **A `model_versions` table** (checkpoint path, architecture, trained-on-dataset metadata,
   `is_active` flag) — `Prediction` would gain a `model_version_id` FK, so every historical
   prediction stays attributed to the model that produced it even after a newer model ships.
2. **`PredictionService` takes a model version, not a hardcoded path.** Right now it always loads
   `settings.model_weights_path`; parameterizing that (and keeping the `@lru_cache`'d loader
   keyed by version, not a bare singleton) lets `/predict` accept an optional `model_version`
   argument and route to the right checkpoint.
3. **`config.yaml`'s `model.architecture` field already exists** for swapping backbones (ResNet-50
   today; a config-driven `build_model()` could dispatch on `architecture` to support ViT/DenseNet
   variants without route changes).
4. For actually serving multiple models concurrently under load (not just multiple *versions*
   sequentially), the next step would be separate model-serving processes (e.g. one Gunicorn
   worker pool per model, or a dedicated inference service behind the API) rather than loading
   every model into the same process's memory.
