"""Request/response models for POST /predict/{study_id}."""
from pydantic import BaseModel


class PredictResponse(BaseModel):
    prediction_id: int
    study_id: int
    disease_labels: dict[str, float]
    gradcam_path: str
    report_text: str | None = None
