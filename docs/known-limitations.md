# Known Limitations

Written honestly, not hidden — a project that names its own limitations is more credible than one
that doesn't have any listed.

## Model / data

- **Only ~300 real training images have been used**, for a quick pipeline check
  (`scripts/download_sample_data.py`), not a real training run. Val AUC climbed 0.57 → 0.70 over 3
  epochs — proof the pipeline learns, nowhere near the documented AUC ≥ 0.90 target or a
  clinically usable model.
- **No clinical validation.** Grad-CAM heatmaps have not been reviewed by a radiologist for
  plausibility; "the pipeline produces a heatmap" is not the same claim as "the heatmap highlights
  the right region."
- **No LR scheduler, no stratified train/val split, no checkpoint resume** — see
  [model.md](model.md) for detail on each.
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
