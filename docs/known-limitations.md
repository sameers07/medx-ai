# Known Limitations

Written honestly, not hidden — a project that names its own limitations is more credible than one
that doesn't have any listed.

## Model / data

- **Only ~2,000 real training images have been used** (`scripts/download_sample_data.py`) — a
  meaningful step up from an earlier 300-image run, but still nowhere near the scale (or the
  documented AUC ≥ 0.90 target) a clinically usable model would need. Best val AUC observed:
  **0.72** (epoch 3 of 10, seeded run) — see [model.md](model.md).
- **The model overfits within ~3-5 epochs at this dataset size** — training loss keeps dropping
  while validation AUC plateaus and drifts down. Observed on three separate runs, so it's a real
  characteristic of training at this scale, not noise. Checkpoint selection now saves the best
  epoch rather than the last (see [model.md](model.md)), which avoids *shipping* the overfit
  model, but doesn't fix the overfitting itself — more data and/or explicit early stopping would.
- **No clinical validation.** Grad-CAM heatmaps have not been reviewed by a radiologist for
  plausibility; "the pipeline produces a heatmap" is not the same claim as "the heatmap highlights
  the right region." In at least one generated heatmap, attention landed partly on an image
  marker/annotation rather than lung tissue — a concrete example of why this gap matters, not a
  hypothetical one.
- **No stratified train/val split, no checkpoint resume (optimizer state/epoch count aren't
  saved)** — see [model.md](model.md) for detail. (A pos_weight class-imbalance correction and an
  LR scheduler were both real gaps here too, and are now fixed.)
- **Single architecture, single active model.** No ensembling, no A/B comparison between model
  versions, no way to roll back to a previous checkpoint's predictions independently of new ones.

## Regulatory / clinical use

- **Not FDA approved, not CE marked, not validated against any regulatory framework.** This is an
  educational/portfolio project, not a medical device.
- **Educational purpose only** — outputs (disease probabilities, Grad-CAM heatmaps, LLM-generated
  reports) must not be used for actual clinical decision-making.
- **No PACS/DICOM integration.** Accepts plain PNG/JPEG uploads, not the DICOM format real
  radiology systems use — no support for DICOM metadata, multi-frame studies, or PACS query/
  retrieve.

## Security / access control

- **Authentication is not implemented.** `/upload`, `/predict/{study_id}`, and
  `/history/{patient_id}` have no access control at all — anyone who can reach the API can read
  any patient's data. The `users` table and `Prediction.user_id` FK exist in the schema
  (`app/database/user_model.py`) but nothing populates or checks them. This is the single biggest
  gap for anything beyond a local demo.
- **Audit logging is limited** to the request-logging middleware (method, path, status, request
  ID) — there is no structured "who viewed which patient's data when" audit trail, which real
  healthcare compliance (e.g. HIPAA) would require.
- **No rate limiting, no TLS termination configured** in this repo (see
  [deployment.md](deployment.md)).

## Infrastructure

- **`storage/` is local filesystem**, bind-mounted into containers — not object storage (S3/GCS).
  Doesn't scale past a single host and has no redundancy.
- **No model versioning.** See [system-design.md](system-design.md)'s "scaling to multiple models"
  for the concrete gap and what fixing it would look like.
- **LLM report generation depends on an external API** (OpenAI by default) — no local/offline
  fallback model. Handled gracefully (`report_text: null` on failure, not a broken request), but
  the feature is unavailable without external network access and a valid key.
