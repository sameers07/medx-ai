# API Reference

Live, always-in-sync interactive docs: `GET /docs` (Swagger UI) once the app is running.

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/` | Root health message | ✅ |
| GET | `/health` | Health check | ✅ |
| POST | `/upload` | Upload + validate + save an image, returns a `study_id` | ✅ |
| POST | `/predict/{study_id}` | Run prediction + Grad-CAM + LLM report on an uploaded study | ✅ (`report_text` is `null` if no `LLM_API_KEY` is configured or the LLM call fails) |
| GET | `/history/{patient_id}` | Retrieve past predictions for a patient (`patient_id` = external ID used in `/upload`), most recent first | ✅ |
| GET | `/storage/{path}` | Static file serving for uploaded images + generated Grad-CAM heatmaps | ✅ |

---

## GET /health

**Response `200`**
```json
{"status": "healthy"}
```

---

## POST /upload

Validates an uploaded image, saves it to disk, and creates (or reuses) a `Patient` + a new `Study`
row. Does not touch the model — see [system-design.md](system-design.md) for why upload and
predict are separate endpoints.

**Request** — `multipart/form-data`

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | file | yes | `.png`, `.jpg`, `.jpeg` only |
| `patient_external_id` | string (form field) | yes | Caller-supplied patient identifier. Reused across uploads for the same patient — a second upload with the same value attaches a new `Study` to the *existing* `Patient` rather than creating a duplicate. |

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@xray.png;type=image/png" \
  -F "patient_external_id=patient-001"
```

**Response `201`**
```json
{"study_id": 1, "patient_id": 1, "image_path": "storage/uploads/patient-001/xray.png"}
```

**Errors**
| Status | When |
|---|---|
| `400` | Unsupported file extension, or the file isn't a readable image (`ImageService.validate()` raises `InvalidImageError`) |
| `422` | Missing `file` or `patient_external_id` (FastAPI's own request validation, before the route body runs) |
| `500` | Unhandled error — caught by the global exception handler (`app/core/exceptions.py`), logged, returns `{"detail": "Internal server error"}` without leaking internals |

---

## POST /predict/{study_id}

Runs the trained model on an already-uploaded study: preprocess → ResNet-50 → sigmoid → Grad-CAM →
LLM report → persist a `Prediction` row.

**Path parameter:** `study_id` (int) — from a prior `/upload` response.

```bash
curl -X POST http://localhost:8000/predict/1
```

**Response `201`**
```json
{
  "prediction_id": 1,
  "study_id": 1,
  "disease_labels": {
    "Atelectasis": 0.11, "Cardiomegaly": 0.99, "Effusion": 0.99, "Infiltration": 0.02,
    "Mass": 0.33, "Nodule": 0.01, "Pneumonia": 0.00, "Pneumothorax": 0.58,
    "Consolidation": 0.99, "Edema": 0.99, "Emphysema": 0.99, "Fibrosis": 0.14,
    "Pleural_Thickening": 0.99, "Hernia": 0.04
  },
  "gradcam_path": "storage/gradcam/xray_heatmap.png",
  "report_text": "Findings are consistent with cardiomegaly and bilateral effusion..."
}
```
`disease_labels` always has all 14 classes from `config.yaml`'s `model.class_names`, each an
independent sigmoid probability (multi-label, not softmax — more than one can and often should be
"positive"). `report_text` is `null`, not an error, if no `LLM_API_KEY` is configured or the LLM
call fails — see [system-design.md](system-design.md)'s graceful-degradation note.

**Errors**
| Status | When |
|---|---|
| `404` | No `Study` with that `study_id` |
| `503` | No trained checkpoint at `settings.model_weights_path` — run `training/train.py` first. Deliberately not `500`: this is an expected, recoverable "not ready yet" state, not a bug. |
| `500` | Any other unhandled failure during preprocessing/inference/Grad-CAM |

---

## GET /history/{patient_id}

**Path parameter:** `patient_id` (string) — the *external* ID passed as `patient_external_id` to
`/upload`, not an internal database row id.

```bash
curl http://localhost:8000/history/patient-001
```

**Response `200`**
```json
{
  "patient_id": "patient-001",
  "predictions": [
    {
      "prediction_id": 2, "study_id": 1,
      "disease_labels": {"...": 0.0},
      "gradcam_path": "storage/gradcam/xray_heatmap.png",
      "report_text": null,
      "created_at": "2026-07-24T05:59:10"
    }
  ]
}
```
`predictions` is ordered most-recent-first by `id`, not `created_at` — see the comment in
`app/api/routes/history.py` (SQLite's `CURRENT_TIMESTAMP` only has second resolution, so two
predictions in the same second would otherwise sort ambiguously; this was caught as a real test
failure, not a hypothetical). An empty `predictions` list is a valid `200` (patient exists, no
predictions yet) — it is not a `404`.

**Errors**
| Status | When |
|---|---|
| `404` | No `Patient` with that external id |

---

## Status code summary

| Code | Meaning here |
|---|---|
| `200` | Successful `GET` |
| `201` | Successful `POST` that created a resource (`Study` or `Prediction`) |
| `400` | Client sent something invalid (bad file) |
| `404` | Referenced resource (`study_id` / `patient_id`) doesn't exist |
| `422` | FastAPI/Pydantic request validation failure (missing/malformed fields) — before route code runs |
| `503` | Service temporarily can't fulfill the request for an expected reason (no trained model yet) |
| `500` | Unhandled exception — always a bug to investigate, never leaks a stack trace to the client |
