"""Build grid rows and plot series from session state.

Extracted from the rendering logic in app.py.
"""
from __future__ import annotations

from typing import Any

from utils import parse_time, format_time_hhmm


def _hours_to_ms(hours_float: float) -> int:
    return int(float(hours_float) * 3_600_000.0)


def build_trains_payload(session: Any) -> dict[str, Any]:
    """Return everything the frontend needs: grid rows, column defs, plot series, axes."""
    sheets_data: list[dict] = session.get("sheets_data", [])
    station_map: dict = session.get("station_map", {})
    station_maps: dict = session.get("station_maps", {})
    selected_sheet: str = session.get("selected_sheet", "")
    train_colors: dict = session.get("train_colors", {})

    if not station_map or not sheets_data:
        return _empty_payload(selected_sheet, train_colors)

    # Active sheet data
    active = next((e for e in sheets_data if e.get("sheet") == selected_sheet), {"trains": []})
    trains_active: list[dict] = active.get("trains", [])

    active_station_map = station_maps.get(selected_sheet, station_map)
    station_items = sorted(active_station_map.items(), key=lambda kv: kv[1])

    # Unique train numbers from active sheet
    unique_trains: list[str] = list(dict.fromkeys(str(t["train_number"]) for t in trains_active))

    # Build cell_map: {(station, km): {train_number: {"p": (display, decimal), ...}}}
    cell_map: dict[tuple, dict] = {}
    for rec in trains_active:
        key = (rec["station"], float(rec["km"]))
        bucket = cell_map.setdefault(key, {})
        tdec = _safe_decimal(rec)
        if tdec is not None:
            display_val = format_time_hhmm(tdec)
        else:
            display_val = str(rec.get("time") or "")
        stop_type = rec.get("stop_type", "p")
        bucket.setdefault(str(rec["train_number"]), {})[stop_type] = (display_val, tdec)

    dual_stations: set[tuple] = set()
    for key, times_dict in cell_map.items():
        if any("o" in v for v in times_dict.values()):
            dual_stations.add(key)

    # Grid rows
    grid_rows: list[dict] = []
    for station, km in station_items:
        times = cell_map.get((station, float(km)), {})
        if (station, float(km)) in dual_stations:
            row_p: dict[str, Any] = {"km": f"{km:.3f}", "stacja": f"{station} (p)",
                                     "_station_raw": station, "_stop_type": "p", "_decimals": {}}
            for tn in unique_trains:
                cell = times.get(tn, {}).get("p")
                row_p[tn] = cell[0] if cell else ""
                if cell and cell[1] is not None:
                    row_p["_decimals"][tn] = cell[1]
            grid_rows.append(row_p)
            row_o: dict[str, Any] = {"km": f"{km:.3f}", "stacja": f"{station} (o)",
                                     "_station_raw": station, "_stop_type": "o", "_decimals": {}}
            for tn in unique_trains:
                cell = times.get(tn, {}).get("o")
                row_o[tn] = cell[0] if cell else ""
                if cell and cell[1] is not None:
                    row_o["_decimals"][tn] = cell[1]
            grid_rows.append(row_o)
        else:
            row: dict[str, Any] = {"km": f"{km:.3f}", "stacja": station,
                                   "_station_raw": station, "_stop_type": None, "_decimals": {}}
            for tn in unique_trains:
                cell = times.get(tn, {}).get("p")
                row[tn] = cell[0] if cell else ""
                if cell and cell[1] is not None:
                    row["_decimals"][tn] = cell[1]
            grid_rows.append(row)

    # Column defs
    column_defs = [
        {"field": "km", "headerName": "km", "editable": False, "width": 60},
        {"field": "stacja", "headerName": "stacja", "editable": False, "width": 60},
    ] + [{"field": c, "headerName": c, "editable": True, "width": 120} for c in unique_trains]

    # Plot series (all sheets)
    series, global_min_ms, global_max_ms = _build_plot_series(sheets_data, station_items)

    pad_left = 2 * 60 * 60 * 1000
    pad_right = 30 * 60 * 1000
    x_min = max(0, (global_min_ms or 0) - pad_left)
    x_max = (global_max_ms or 24 * 3_600_000) + pad_right

    return {
        "grid_rows": grid_rows,
        "column_defs": column_defs,
        "plot_series": series,
        "station_items": [{"name": n, "km": float(k)} for n, k in station_items],
        "x_min_ms": x_min,
        "x_max_ms": x_max,
        "train_colors": train_colors,
        "selected_sheet": selected_sheet,
    }


def _safe_decimal(rec: dict) -> float | None:
    try:
        td = rec.get("time_decimal")
        if td is not None:
            return float(td)
    except (ValueError, TypeError):
        pass
    parsed = parse_time(rec.get("time"))
    return float(parsed) if parsed is not None else None


def _build_plot_series(
    sheets_data: list[dict],
    station_items: list[tuple[str, float]],
) -> tuple[list[dict], int | None, int | None]:
    """Build plot series from all sheets. Returns (series, global_min_ms, global_max_ms)."""
    sheet_to_station_train: dict[str, dict] = {}
    sheet_to_trains: dict[str, list[str]] = {}

    for entry in sheets_data:
        sheet = entry.get("sheet")
        station_to_train: dict[str, dict[str, list]] = {}
        trains = entry.get("trains", [])
        for rec in trains:
            sn = rec["station"]
            tn = str(rec["train_number"])
            station_to_train.setdefault(sn, {}).setdefault(tn, []).append({
                "time_decimal": rec.get("time_decimal"),
                "stop_type": rec.get("stop_type"),
            })
        sheet_to_station_train[sheet] = station_to_train
        sheet_to_trains[sheet] = sorted({str(t["train_number"]) for t in trains})

    series: list[dict] = []
    global_min_ms: int | None = None
    global_max_ms: int | None = None

    for sheet, station_to_train in sheet_to_station_train.items():
        for tn in sheet_to_trains.get(sheet, []):
            pts: list[dict] = []
            for station_name, km_selected in station_items:
                times_list = station_to_train.get(station_name, {}).get(tn)
                if not times_list:
                    continue
                for info in times_list:
                    t_dec = info["time_decimal"]
                    if t_dec is None:
                        continue
                    ms = _hours_to_ms(t_dec)
                    pts.append({
                        "value": [ms, float(km_selected)],
                        "station": station_name,
                        "train": tn,
                        "sheet": sheet,
                        "stopType": info["stop_type"],
                    })
                    global_min_ms = ms if global_min_ms is None else min(global_min_ms, ms)
                    global_max_ms = ms if global_max_ms is None else max(global_max_ms, ms)
            if pts:
                pts = _sort_points_by_direction(pts)
                series.append({"name": f"{tn} ({sheet})", "points": pts})

    return series, global_min_ms, global_max_ms


def _sort_points_by_direction(pts: list[dict]) -> list[dict]:
    """Sort points by km in the detected travel direction."""
    pts.sort(key=lambda p: p["value"][1])
    asc_votes = 0
    desc_votes = 0
    for i in range(1, len(pts)):
        if pts[i]["value"][1] == pts[i - 1]["value"][1]:
            continue
        if pts[i]["value"][0] > pts[i - 1]["value"][0]:
            asc_votes += 1
        elif pts[i]["value"][0] < pts[i - 1]["value"][0]:
            desc_votes += 1
    if desc_votes > asc_votes:
        pts.sort(key=lambda p: (-p["value"][1], p["value"][0]))
    else:
        pts.sort(key=lambda p: (p["value"][1], p["value"][0]))
    return pts


def _empty_payload(selected_sheet: str, train_colors: dict) -> dict[str, Any]:
    return {
        "grid_rows": [],
        "column_defs": [],
        "plot_series": [],
        "station_items": [],
        "x_min_ms": 0,
        "x_max_ms": 24 * 3_600_000,
        "train_colors": train_colors,
        "selected_sheet": selected_sheet,
    }
