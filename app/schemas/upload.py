"""Request/response models for POST /upload."""
from pydantic import BaseModel


class UploadResponse(BaseModel):
    study_id: int
    patient_id: int
    image_path: str
