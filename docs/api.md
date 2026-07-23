# API Reference

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/` | Root health message | ✅ |
| GET | `/health` | Health check | ✅ |
| POST | `/upload` | Upload + validate + save an image, returns a `study_id` | ✅ |
| POST | `/predict/{study_id}` | Run prediction + Grad-CAM + LLM report on an uploaded study | ✅ (`report_text` is `null` if no `LLM_API_KEY` is configured or the LLM call fails — doesn't fail the request) |
| GET | `/history/{patient_id}` | Retrieve past predictions for a patient | 🚧 stub |
