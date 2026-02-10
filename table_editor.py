from typing import Any, Dict, List, Optional, Tuple
import datetime as _dt

from utils import format_time_decimal


def save_cell_time(
    selected_sheet: str,
    station: str,
    km: float,
    train_number: str,
    time_value: _dt.time,
    session_state: Any,
    day_offset: int = 0,
    stop_type: Optional[str] = None,
) -> None:
    """Save a single cell time into session_state for the given sheet.

    If record exists, it is updated; otherwise it is created.
    ``day_offset`` adds full days (24 h each) to the stored decimal so that
    midnight-crossing times are preserved correctly.
    ``stop_type`` selects which record to update when multiple records share
    the same (station, km, train_number) key ("p" = arrival, "o" = departure,
    None = non-dual station).
    """
    sheets_data: List[Dict[str, Any]] = session_state.get("sheets_data", [])
    active = next((s for s in sheets_data if s.get("sheet") == selected_sheet), None)
    if active is None:
        return
    trains_list: List[Dict[str, Any]] = active.get("trains", [])

    key = (station, float(km), str(train_number))

    def rec_key(r: Dict[str, Any]) -> Tuple[str, float, str]:
        return (r["station"], float(r["km"]), str(r["train_number"]))

    # compute decimal and canonical string
    h = int(time_value.hour)
    m = int(getattr(time_value, "minute", 0) or 0)
    s = int(getattr(time_value, "second", 0) or 0)
    decimal = h + m / 60 + s / 3600 + day_offset * 24
    canonical = format_time_decimal(float(decimal))

    # Find matching record by stop_type
    target_idx = None
    for i, r in enumerate(trains_list):
        if rec_key(r) == key and r.get("stop_type") == stop_type:
            target_idx = i
            break

    if target_idx is not None:
        trains_list[target_idx]["time"] = canonical
        trains_list[target_idx]["time_decimal"] = float(decimal)
    else:
        new_rec = {
            "train_number": str(train_number),
            "station": station,
            "km": float(km),
            "time": canonical,
            "time_decimal": float(decimal),
        }
        if stop_type is not None:
            new_rec["stop_type"] = stop_type
        trains_list.append(new_rec)

    active["trains"] = trains_list
    for i, s in enumerate(sheets_data):
        if s.get("sheet") == selected_sheet:
            sheets_data[i] = active
            break
    session_state["sheets_data"] = sheets_data


def clear_cell_time(
    selected_sheet: str,
    station: str,
    km: float,
    train_number: str,
    session_state: Any,
    stop_type: Optional[str] = None,
) -> None:
    """Clear a single cell time (remove record) in session_state for the given sheet.

    ``stop_type`` selects which record to remove when multiple records share
    the same (station, km, train_number) key ("p" = arrival, "o" = departure,
    None = non-dual station).
    """
    sheets_data: List[Dict[str, Any]] = session_state.get("sheets_data", [])
    active = next((s for s in sheets_data if s.get("sheet") == selected_sheet), None)
    if active is None:
        return
    trains_list: List[Dict[str, Any]] = active.get("trains", [])

    key = (station, float(km), str(train_number))

    def rec_key(r: Dict[str, Any]) -> Tuple[str, float, str]:
        return (r["station"], float(r["km"]), str(r["train_number"]))

    target_idx = None
    for i, r in enumerate(trains_list):
        if rec_key(r) == key and r.get("stop_type") == stop_type:
            target_idx = i
            break

    if target_idx is not None:
        del trains_list[target_idx]

    active["trains"] = trains_list
    for i, s in enumerate(sheets_data):
        if s.get("sheet") == selected_sheet:
            sheets_data[i] = active
            break
    session_state["sheets_data"] = sheets_data


def propagate_time_shift(
    selected_sheet: str,
    train_number: str,
    from_km: float,
    delta_hours: float,
    session_state: Any,
) -> None:
    """Propagate a time shift to downstream stations for the given train.

    Detects travel direction (ascending or descending km) from the train's
    existing data.  Only adjusts records that already have a time.  Handles
    day crossing via decimal hours (format_time_decimal will render (+d) if
    needed).
    """
    sheets_data: List[Dict[str, Any]] = session_state.get("sheets_data", [])
    active = next((s for s in sheets_data if s.get("sheet") == selected_sheet), None)
    if active is None:
        return
    trains_list: List[Dict[str, Any]] = active.get("trains", [])

    # Collect all records for this train that have valid time_decimal
    train_recs = [
        r for r in trains_list
        if str(r.get("train_number")) == str(train_number) and r.get("time_decimal") is not None
    ]

    if len(train_recs) < 2:
        # Not enough data to determine direction; nothing to propagate
        return

    # Detect direction: sort by km ascending, compare first vs last time
    sorted_by_km = sorted(train_recs, key=lambda r: float(r.get("km", 0.0)))
    first_time = float(sorted_by_km[0].get("time_decimal", 0.0))
    last_time = float(sorted_by_km[-1].get("time_decimal", 0.0))
    ascending = last_time >= first_time  # True = forward (km increases with time)

    for rec in trains_list:
        if str(rec.get("train_number")) != str(train_number):
            continue
        km_val = float(rec.get("km", 0.0))
        if ascending:
            if km_val <= float(from_km):
                continue
        else:
            if km_val >= float(from_km):
                continue
        t_dec = rec.get("time_decimal")
        if t_dec is None:
            continue
        try:
            new_dec = float(t_dec) + float(delta_hours)
        except Exception:
            continue
        if new_dec < 0:
            new_dec = new_dec % 24
        rec["time_decimal"] = new_dec
        rec["time"] = format_time_decimal(new_dec)

    active["trains"] = trains_list
    for i, s in enumerate(sheets_data):
        if s.get("sheet") == selected_sheet:
            sheets_data[i] = active
            break
    session_state["sheets_data"] = sheets_data


