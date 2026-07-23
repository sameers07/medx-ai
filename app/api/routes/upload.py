"""POST /upload — validate and store an uploaded chest X-ray image. No model inference here."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.database.patient_model import Patient, Study
from app.schemas.upload import UploadResponse
from app.services.image_service import ImageService, InvalidImageError
from app.services.storage_service import StorageService

router = APIRouter(tags=["upload"])

image_service = ImageService()
storage_service = StorageService()


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    patient_external_id: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        image_service.validate(file)
    except InvalidImageError as e:
        raise HTTPException(status_code=400, detail=str(e))

    patient = db.query(Patient).filter_by(external_id=patient_external_id).first()
    if patient is None:
        patient = Patient(external_id=patient_external_id)
        db.add(patient)
        db.flush()

    image_path = storage_service.save(file, f"uploads/{patient.external_id}/{file.filename}")

    study = Study(patient_id=patient.id, image_path=image_path)
    db.add(study)
    db.commit()
    db.refresh(study)

    return UploadResponse(study_id=study.id, patient_id=patient.id, image_path=image_path)
