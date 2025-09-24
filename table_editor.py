from typing import List, Dict, Tuple, Any, Optional
import datetime as _dt

import pandas as pd

from utils import parse_time, format_time_decimal


def _strip_day_suffix(value: str) -> str:
    """Remove optional day suffix like ' (+1)' from time strings."""
    s = str(value).strip()
    # simple cut at first space before '(' if present
    if "(" in s:
        s = s.split("(", 1)[0].strip()
    return s


def _to_float_km(km_str: str) -> float:
    try:
        return float(str(km_str).replace(",", "."))
    except Exception:
        return float("nan")


def apply_table_edits(
    selected_sheet: str,
    original_df: pd.DataFrame,
    edited_df: pd.DataFrame,
    session_state,
) -> List[str]:
    """Apply edits from edited_df back into session_state['sheets_data'] for selected_sheet.

    - Assumes df has columns: 'km', 'stacja', and train numbers as remaining columns.
    - Values should be 'HH:MM' (empty string clears value).
    - Performs basic validation using utils.parse_time after stripping '(+d)'.
    Returns list of validation error messages.
    """
    errors: List[str] = []

    # Identify train columns
    non_train_cols = {"km", "stacja"}
    train_cols = [c for c in edited_df.columns if c not in non_train_cols]

    # Build quick access to active sheet trains list
    sheets_data: List[Dict[str, any]] = session_state.get("sheets_data", [])
    active = next((s for s in sheets_data if s.get("sheet") == selected_sheet), None)
    if active is None:
        return ["Nie znaleziono danych dla wybranego arkusza."]
    trains_list: List[Dict[str, any]] = active.get("trains", [])

    # Index existing records by (station, km, train_number)
    def key_of(rec: Dict[str, any]) -> Tuple[str, float, str]:
        return (rec["station"], float(rec["km"]), str(rec["train_number"]))

    records_by_key: Dict[Tuple[str, float, str], Dict[str, any]] = {
        key_of(rec): rec for rec in trains_list
    }

    # Walk through rows and columns to find changes
    for idx in range(len(edited_df)):
        station = str(edited_df.at[idx, "stacja"]).strip()
        km_val = _to_float_km(edited_df.at[idx, "km"]).__float__()
        for train in train_cols:
            old_val = str(original_df.at[idx, train]) if train in original_df.columns else ""
            new_val = str(edited_df.at[idx, train])

            if new_val == old_val:
                continue

            rec_key = (station, km_val, str(train))

            # Empty string clears value
            if new_val.strip() == "":
                if rec_key in records_by_key:
                    # remove from list
                    rec = records_by_key.pop(rec_key)
                    try:
                        trains_list.remove(rec)
                    except ValueError:
                        pass
                continue

            # Validate and normalize time
            parsed = parse_time(_strip_day_suffix(new_val))
            if parsed is None:
                errors.append(
                    f"Niepoprawny czas w wierszu {idx + 1}, pociąg {train}, stacja {station}: '{new_val}'"
                )
                continue

            canonical_str = format_time_decimal(float(parsed))

            if rec_key in records_by_key:
                rec = records_by_key[rec_key]
                rec["time"] = canonical_str
                rec["time_decimal"] = float(parsed)
            else:
                new_rec = {
                    "train_number": str(train),
                    "station": station,
                    "km": float(km_val),
                    "time": canonical_str,
                    "time_decimal": float(parsed),
                }
                trains_list.append(new_rec)
                records_by_key[rec_key] = new_rec

    # Persist back to session_state (active already references the list)
    active["trains"] = trains_list
    # Replace the entry in sheets_data to be safe
    for i, s in enumerate(sheets_data):
        if s.get("sheet") == selected_sheet:
            sheets_data[i] = active
            break
    session_state["sheets_data"] = sheets_data

    return errors


def save_cell_time(
    selected_sheet: str,
    station: str,
    km: float,
    train_number: str,
    time_value: _dt.time,
    session_state: Any,
) -> None:
    """Save a single cell time into session_state for the given sheet.

    If record exists, it is updated; otherwise it is created.
    """
    sheets_data: List[Dict[str, any]] = session_state.get("sheets_data", [])
    active = next((s for s in sheets_data if s.get("sheet") == selected_sheet), None)
    if active is None:
        return
    trains_list: List[Dict[str, any]] = active.get("trains", [])

    key = (station, float(km), str(train_number))

    def rec_key(r: Dict[str, any]) -> Tuple[str, float, str]:
        return (r["station"], float(r["km"]), str(r["train_number"]))

    # compute decimal and canonical string
    h = int(time_value.hour)
    m = int(getattr(time_value, "minute", 0) or 0)
    s = int(getattr(time_value, "second", 0) or 0)
    decimal = h + m / 60 + s / 3600
    canonical = format_time_decimal(float(decimal))

    try:
        print("DBG save_cell_time key:", key)
        print("DBG trains_list size (before):", len(trains_list))
    except Exception:
        pass

    found_index = None
    for idx, r in enumerate(trains_list):
        if rec_key(r) == key:
            r["time"] = canonical
            r["time_decimal"] = float(decimal)
            found_index = idx
            break

    if found_index is None:
        updated_rec = {
            "train_number": str(train_number),
            "station": station,
            "km": float(km),
            "time": canonical,
            "time_decimal": float(decimal),
        }
        trains_list.append(updated_rec)
        try:
            print("DBG save_cell_time appended new record for:", key)
        except Exception:
            pass
    else:
        # Przenieś zaktualizowany rekord na koniec i usuń pozostałe duplikaty tego klucza
        try:
            updated_rec = trains_list[found_index]
            remainder = [r for i, r in enumerate(trains_list) if rec_key(r) != key or i == found_index]
            base = [r for i, r in enumerate(remainder) if rec_key(r) != key or i == found_index]
        except Exception:
            updated_rec = trains_list[found_index]
            base = [r for i, r in enumerate(trains_list) if i != found_index and rec_key(r) != key]
        # Usuń wszystkie o tym samym kluczu, zachowaj jeden zaktualizowany na końcu
        base = [r for r in trains_list if rec_key(r) != key]
        base.append(updated_rec)
        trains_list[:] = base

    try:
        print("DBG trains_list size (after):", len(trains_list))
    except Exception:
        pass

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
) -> None:
    """Clear a single cell time (remove record) in session_state for the given sheet."""
    sheets_data: List[Dict[str, any]] = session_state.get("sheets_data", [])
    active = next((s for s in sheets_data if s.get("sheet") == selected_sheet), None)
    if active is None:
        return
    trains_list: List[Dict[str, any]] = active.get("trains", [])

    key = (station, float(km), str(train_number))

    def rec_key(r: Dict[str, any]) -> Tuple[str, float, str]:
        return (r["station"], float(r["km"]), str(r["train_number"]))

    new_list = [r for r in trains_list if rec_key(r) != key]
    active["trains"] = new_list
    for i, s in enumerate(sheets_data):
        if s.get("sheet") == selected_sheet:
            sheets_data[i] = active
            break
    session_state["sheets_data"] = sheets_data


