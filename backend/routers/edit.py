import datetime as dt

from fastapi import APIRouter, Depends

from backend.deps import get_state
from backend.models.session import SessionState
from backend.models.requests import SaveTimeRequest, ClearTimeRequest
from backend.services.plot_data import build_trains_payload
from table_editor import save_cell_time, clear_cell_time, propagate_time_shift
from utils import parse_time

router = APIRouter(prefix="/api/edit", tags=["edit"])


@router.post("/save")
async def save_time(
    body: SaveTimeRequest,
    session: SessionState = Depends(get_state),
) -> dict:
    time_value = dt.time(body.hour, body.minute, body.second)

    if body.propagate:
        # Compute delta from existing time
        sheets_data = session.get("sheets_data", [])
        active = next((s for s in sheets_data if s.get("sheet") == body.sheet), None)
        old_decimal = None
        if active:
            for rec in active.get("trains", []):
                if (str(rec.get("train_number")) == body.train_number
                        and rec.get("station") == body.station
                        and abs(float(rec.get("km", 0)) - body.km) < 0.01
                        and rec.get("stop_type") == body.stop_type):
                    old_decimal = rec.get("time_decimal")
                    break

        if old_decimal is not None:
            new_dec = body.hour + body.minute / 60.0 + body.second / 3600.0
            parsed_norm = float(old_decimal) % 24
            delta_hours = new_dec - parsed_norm
            if delta_hours > 12:
                delta_hours -= 24
            elif delta_hours < -12:
                delta_hours += 24
            if delta_hours != 0.0:
                propagate_time_shift(body.sheet, body.train_number, body.km, delta_hours, session)

    save_cell_time(
        body.sheet, body.station, body.km, body.train_number,
        time_value, session,
        day_offset=body.day_offset, stop_type=body.stop_type,
    )
    return build_trains_payload(session)


@router.post("/clear")
async def clear_time(
    body: ClearTimeRequest,
    session: SessionState = Depends(get_state),
) -> dict:
    clear_cell_time(
        body.sheet, body.station, body.km, body.train_number,
        session, stop_type=body.stop_type,
    )
    return build_trains_payload(session)
