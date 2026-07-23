"""POST /predict — stub only, no AI wired in yet."""
from fastapi import APIRouter, UploadFile, File

router = APIRouter(tags=["predict"])


@router.post("/predict")
async def predict(file: UploadFile = File(...)):
    return {"message": "Coming Soon"}
