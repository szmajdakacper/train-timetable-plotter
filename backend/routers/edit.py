import datetime as dt

from fastapi import APIRouter, Depends

from backend.deps import get_state
from backend.models.session import SessionState
from backend.models.requests import SaveTimeRequest, ClearTimeRequest
from backend.services.plot_data import build_trains_payload
from table_editor import save_cell_time, clear_cell_time, propagate_time_shift

router = APIRouter(prefix="/api/edit", tags=["edit"])


def _canonical_km(session: SessionState, sheet: str, station: str, fallback_km: float) -> float:
    """Look up the canonical km for a station from its own sheet's station map.

    The plot may display a train from sheet A using sheet B's km values.
    propagate_time_shift and save_cell_time need the km from the train's
    own sheet so comparisons against record km values work correctly.
    """
    station_maps = session.get("station_maps", {})
    sheet_map = station_maps.get(sheet, {})
    km = sheet_map.get(station)
    if km is not None:
        return float(km)
    return fallback_km


@router.post("/save")
async def save_time(
    body: SaveTimeRequest,
    session: SessionState = Depends(get_state),
) -> dict:
    time_value = dt.time(body.hour, body.minute, body.second)

    # Resolve km from the train's own sheet (plot may send active-sheet km)
    km = _canonical_km(session, body.sheet, body.station, body.km)

    if body.propagate:
        # Compute delta from existing time
        sheets_data = session.get("sheets_data", [])
        active = next((s for s in sheets_data if s.get("sheet") == body.sheet), None)
        old_decimal = None
        if active:
            for rec in active.get("trains", []):
                if (str(rec.get("train_number")) == body.train_number
                        and rec.get("station") == body.station
                        and abs(float(rec.get("km", 0)) - km) < 0.01
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
                propagate_time_shift(body.sheet, body.train_number, km, delta_hours, session)

    save_cell_time(
        body.sheet, body.station, km, body.train_number,
        time_value, session,
        day_offset=body.day_offset, stop_type=body.stop_type,
    )
    return build_trains_payload(session)


@router.post("/clear")
async def clear_time(
    body: ClearTimeRequest,
    session: SessionState = Depends(get_state),
) -> dict:
    km = _canonical_km(session, body.sheet, body.station, body.km)
    clear_cell_time(
        body.sheet, body.station, km, body.train_number,
        session, stop_type=body.stop_type,
    )
    return build_trains_payload(session)
