from fastapi import APIRouter, Depends

from backend.deps import get_state
from backend.models.session import SessionState
from backend.services.plot_data import build_trains_payload

router = APIRouter(prefix="/api", tags=["trains"])


@router.get("/trains")
async def get_trains(session: SessionState = Depends(get_state)) -> dict:
    return build_trains_payload(session)
