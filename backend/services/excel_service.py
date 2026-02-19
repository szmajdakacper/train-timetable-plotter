from __future__ import annotations

import hashlib
import json
from typing import Any

from backend.models.session import SessionState
from excel_loader import read_workbook, extract_excel_data


def load_excel(file_bytes: bytes, filename: str, session: SessionState) -> dict[str, Any]:
    """Parse an Excel file and populate session state. Returns metadata."""
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    if session.get("uploaded_hash") == file_hash:
        return {"changed": False}

    sheet_names, sheets, hidden_cols = read_workbook(file_bytes)
    data = extract_excel_data(sheet_names, sheets, hidden_cols=hidden_cols)

    session["station_map"] = data["station_map"]
    session["station_maps"] = data.get("station_maps", {})
    session["station_check"] = data["station_check"]
    session["sheets_data"] = data["sheets_data"]
    session["uploaded_hash"] = file_hash
    session["uploaded_name"] = filename
    session["train_colors"] = session.get("train_colors") or {}

    sheet_names_out = [e["sheet"] for e in data["sheets_data"]]
    if "selected_sheet" not in session or session["selected_sheet"] not in sheet_names_out:
        session["selected_sheet"] = sheet_names_out[0] if sheet_names_out else ""

    return {"changed": True, "sheets": sheet_names_out}


def load_project_json(file_bytes: bytes, session: SessionState) -> dict[str, Any]:
    """Load a project JSON file and populate session state."""
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    if session.get("uploaded_hash") == file_hash:
        return {"changed": False}

    project = json.loads(file_bytes.decode("utf-8"))

    if project.get("_format") != "train-timetable-plotter-project":
        raise ValueError("Nieprawidlowy format pliku projektu (brak pola _format).")
    if "sheets_data" not in project:
        raise ValueError("Plik projektu nie zawiera danych arkuszy (sheets_data).")

    session["sheets_data"] = project["sheets_data"]
    session["station_map"] = project.get("station_map", {})
    session["station_maps"] = project.get("station_maps", {})
    session["train_colors"] = project.get("train_colors", {})
    session["uploaded_name"] = project.get("uploaded_name", "")
    session["selected_sheet"] = project.get("selected_sheet", "")
    session["uploaded_hash"] = file_hash

    sheet_names = [e["sheet"] for e in project["sheets_data"]]
    return {"changed": True, "sheets": sheet_names}
