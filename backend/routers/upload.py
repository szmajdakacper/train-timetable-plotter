from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from backend.deps import get_state
from backend.models.session import SessionState
from backend.models.responses import UploadResponse
from backend.services.excel_service import load_excel, load_project_json

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    session: SessionState = Depends(get_state),
) -> UploadResponse:
    file_bytes = await file.read()
    filename = file.filename or ""

    if filename.lower().endswith(".json"):
        try:
            result = load_project_json(file_bytes, session)
        except (ValueError, Exception) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    elif filename.lower().endswith(".xlsx"):
        try:
            result = load_excel(file_bytes, filename, session)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Nie udalo sie wczytac pliku: {exc}")
    else:
        raise HTTPException(status_code=400, detail="Nieobslugiwany format pliku. Uzyj .xlsx lub .json.")

    sheets = result.get("sheets", [s["sheet"] for s in session.get("sheets_data", [])])
    selected = session.get("selected_sheet", sheets[0] if sheets else "")
    return UploadResponse(ok=True, sheets=sheets, selected_sheet=selected, message="OK")
