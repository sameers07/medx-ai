"""GET /history/{patient_id} — past predictions for a patient, most recent first.

`patient_id` is the external ID (same value passed as `patient_external_id` to POST /upload),
not the internal DB row id — that's what a caller actually has on hand.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.database.patient_model import Patient, Study
from app.database.prediction_model import Prediction
from app.schemas.history import HistoryItem, HistoryResponse

router = APIRouter(tags=["history"])


@router.get("/history/{patient_id}", response_model=HistoryResponse)
def get_history(patient_id: str, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter_by(external_id=patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id!r} not found")

    predictions = (
        db.query(Prediction)
        .join(Study, Prediction.study_id == Study.id)
        .filter(Study.patient_id == patient.id)
        # id, not created_at — created_at has only second resolution (server_default
        # CURRENT_TIMESTAMP), so two predictions in the same second would sort ambiguously.
        .order_by(Prediction.id.desc())
        .all()
    )

    return HistoryResponse(
        patient_id=patient_id,
        predictions=[
            HistoryItem(
                prediction_id=p.id,
                study_id=p.study_id,
                disease_labels=p.disease_labels or {},
                gradcam_path=p.gradcam_path,
                report_text=p.report_text,
                created_at=p.created_at,
            )
            for p in predictions
        ],
    )
