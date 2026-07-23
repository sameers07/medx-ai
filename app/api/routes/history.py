"""GET /history/{patient_id} — stub only, no DB queries wired in yet."""
from fastapi import APIRouter

router = APIRouter(tags=["history"])


@router.get("/history/{patient_id}")
async def get_history(patient_id: str):
    return {"message": "Coming Soon"}
