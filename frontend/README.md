# frontend

Streamlit UI for MedX AI: upload a chest X-ray, get disease probabilities, a Grad-CAM overlay,
and an LLM-generated report.

## Run

```bash
uvicorn app.api.main:app --reload   # backend, in one terminal
streamlit run frontend/app.py       # frontend, in another
```

Set the backend URL in the sidebar if it's not running on `http://localhost:8000`.
