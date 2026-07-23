"""POST /predict/{study_id} — run prediction + Grad-CAM + report generation on an uploaded study."""
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.logging import get_logger
from app.config.model_config import config
from app.core.dependencies import get_db
from app.database.patient_model import Study
from app.database.prediction_model import Prediction
from app.schemas.predict import PredictResponse
from app.services.gradcam_service import GradCAMService
from app.services.prediction_service import PredictionService
from app.services.report_service import ReportService

router = APIRouter(tags=["predict"])
logger = get_logger(__name__)

_TARGET_LAYER = config["explainability"]["target_layer"]


@lru_cache(maxsize=1)
def get_prediction_service() -> PredictionService:
    """Loaded lazily (and cached) so the app can still boot without a trained checkpoint."""
    return PredictionService()


@lru_cache(maxsize=1)
def get_report_service() -> ReportService:
    return ReportService()


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

    try:
        report_text = get_report_service().generate_report(disease_labels)
    except Exception:
        logger.warning("Report generation failed; leaving report_text null", exc_info=True)
        report_text = None

    prediction = Prediction(
        study_id=study.id,
        disease_labels=disease_labels,
        gradcam_path=gradcam_path,
        report_text=report_text,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    return PredictResponse(
        prediction_id=prediction.id,
        study_id=study.id,
        disease_labels=disease_labels,
        gradcam_path=gradcam_path,
        report_text=report_text,
    )
