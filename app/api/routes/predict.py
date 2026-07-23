"""POST /predict/{study_id} — run prediction + Grad-CAM on an already-uploaded study.

Report generation (feature/report-generator) isn't wired yet, so `report_text` stays null.
"""
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.model_config import config
from app.core.dependencies import get_db
from app.database.patient_model import Study
from app.database.prediction_model import Prediction
from app.schemas.predict import PredictResponse
from app.services.gradcam_service import GradCAMService
from app.services.prediction_service import PredictionService

router = APIRouter(tags=["predict"])

_TARGET_LAYER = config["explainability"]["target_layer"]


@lru_cache(maxsize=1)
def get_prediction_service() -> PredictionService:
    """Loaded lazily (and cached) so the app can still boot without a trained checkpoint."""
    return PredictionService()


@router.post("/predict/{study_id}", response_model=PredictResponse, status_code=201)
def predict(study_id: int, db: Session = Depends(get_db)):
    study = db.get(Study, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail=f"Study {study_id} not found")

    try:
        prediction_service = get_prediction_service()
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="No trained model checkpoint found. Run training/train.py first.",
        )

    disease_labels = prediction_service.predict(study.image_path)
    gradcam_service = GradCAMService()
    gradcam_path = gradcam_service.generate_heatmap(
        study.image_path, prediction_service.model, _TARGET_LAYER
    )

    prediction = Prediction(
        study_id=study.id,
        disease_labels=disease_labels,
        gradcam_path=gradcam_path,
        report_text=None,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    return PredictResponse(
        prediction_id=prediction.id,
        study_id=study.id,
        disease_labels=disease_labels,
        gradcam_path=gradcam_path,
        report_text=None,
    )
