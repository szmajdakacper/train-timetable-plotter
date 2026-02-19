from fastapi import APIRouter, Depends, HTTPException

from backend.deps import get_state
from backend.models.session import SessionState
from backend.models.requests import SelectSheetRequest
from backend.models.responses import SheetsResponse

router = APIRouter(prefix="/api", tags=["sheets"])


@router.get("/sheets", response_model=SheetsResponse)
async def list_sheets(session: SessionState = Depends(get_state)) -> SheetsResponse:
    sheets_data = session.get("sheets_data", [])
    sheets = [e["sheet"] for e in sheets_data]
    selected = session.get("selected_sheet", sheets[0] if sheets else "")
    return SheetsResponse(sheets=sheets, selected_sheet=selected)


@router.put("/sheets/select", response_model=SheetsResponse)
async def select_sheet(
    body: SelectSheetRequest,
    session: SessionState = Depends(get_state),
) -> SheetsResponse:
    sheets_data = session.get("sheets_data", [])
    sheets = [e["sheet"] for e in sheets_data]
    if body.sheet not in sheets:
        raise HTTPException(status_code=404, detail=f"Arkusz '{body.sheet}' nie istnieje.")
    session["selected_sheet"] = body.sheet
    return SheetsResponse(sheets=sheets, selected_sheet=body.sheet)
