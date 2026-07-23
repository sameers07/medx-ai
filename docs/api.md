# API Reference

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/` | Root health message | ✅ |
| GET | `/health` | Health check | ✅ |
| POST | `/upload` | Upload + validate + save an image, returns a `study_id` | ✅ |
| POST | `/predict/{study_id}` | Run prediction + Grad-CAM on an uploaded study | ✅ (report generation not wired yet — `report_text` is always `null`) |
| GET | `/history/{patient_id}` | Retrieve past predictions for a patient | 🚧 stub |
