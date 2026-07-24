"""Request/response models for GET /history/{patient_id}."""
from datetime import datetime

from pydantic import BaseModel


class HistoryItem(BaseModel):
    prediction_id: int
    study_id: int
    disease_labels: dict[str, float]
    gradcam_path: str | None
    report_text: str | None
    created_at: datetime


class HistoryResponse(BaseModel):
    patient_id: str
    predictions: list[HistoryItem]
