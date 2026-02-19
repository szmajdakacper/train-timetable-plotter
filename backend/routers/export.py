import json
import datetime as dt
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.deps import get_state
from backend.models.session import SessionState
from backend.services.export_service import (
    build_excel_bytes,
    build_circuits_excel_bytes,
    build_project_json,
)

router = APIRouter(prefix="/api/export", tags=["export"])


def _content_disposition(filename: str) -> str:
    """Build Content-Disposition header safe for non-ASCII filenames (RFC 5987)."""
    ascii_name = filename.encode("ascii", errors="replace").decode("ascii")
    utf8_name = quote(filename)
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{utf8_name}"


@router.get("/xlsx")
async def export_xlsx(session: SessionState = Depends(get_state)) -> StreamingResponse:
    data = build_excel_bytes(session)
    name = session.get("uploaded_name") or "rozklad.xlsx"
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _content_disposition(name)},
    )


@router.get("/circuits")
async def export_circuits(session: SessionState = Depends(get_state)) -> StreamingResponse:
    data = build_circuits_excel_bytes(session)
    base = (session.get("uploaded_name") or "obiegi").rsplit(".", 1)[0]
    ts = dt.datetime.now().strftime("%H_%M_%d_%m_%Y")
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _content_disposition(f"{base}_obiegi_{ts}.xlsx")},
    )


@router.get("/project")
async def export_project(session: SessionState = Depends(get_state)) -> StreamingResponse:
    data = build_project_json(session)
    base = (session.get("uploaded_name") or "projekt").rsplit(".", 1)[0]
    ts = dt.datetime.now().strftime("%H_%M_%d_%m_%Y")
    return StreamingResponse(
        BytesIO(data),
        media_type="application/json",
        headers={"Content-Disposition": _content_disposition(f"{base}_{ts}.json")},
    )
