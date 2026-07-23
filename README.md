# MedX AI — Advanced AI Medical Intelligence Platform

An end-to-end medical imaging AI system: disease prediction from chest X-rays,
Grad-CAM based explainability, LLM-assisted radiology report generation, and a
REST API + web UI for clinicians.

## Status
🚧 Under active development. See `docs/roadmap.md` for the build plan.

## Stack
- **Model**: CNN/ViT (ResNet-50 baseline) on chest X-ray datasets (MIMIC-CXR / CheXpert / ChestX-ray14)
- **Explainability**: Grad-CAM / Grad-CAM++
- **Reports**: LLM-based narrative report generation
- **API**: FastAPI + PostgreSQL
- **Frontend**: Streamlit
- **Deployment**: Docker / Docker Compose

## Project Structure
See `docs/architecture.md`.

## Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running
```bash
uvicorn app.api.main:app --reload
```

## License
See `LICENSE`.
