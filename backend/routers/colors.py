from fastapi import APIRouter, Depends

from backend.deps import get_state
from backend.models.session import SessionState
from backend.models.requests import SetColorRequest

router = APIRouter(prefix="/api", tags=["colors"])


@router.put("/colors")
async def set_color(
    body: SetColorRequest,
    session: SessionState = Depends(get_state),
) -> dict:
    colors = session.get("train_colors", {})
    if body.color == "#000000":
        colors.pop(body.train_number, None)
    else:
        colors[body.train_number] = body.color
    session["train_colors"] = colors
    return {"train_colors": colors}


@router.delete("/colors/all")
async def clear_all_colors(session: SessionState = Depends(get_state)) -> dict:
    session["train_colors"] = {}
    return {"train_colors": {}}
