# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Train Timetable Plotter is a web app for visualizing and editing train timetables from Excel files. It uses a **React SPA** frontend (TypeScript, Vite, AG Grid, ECharts) with a **FastAPI** backend. It supports JSON project save/load for preserving work across sessions. The UI and comments are largely in Polish.

## Commands

### Run the app (development)
```bash
# Terminal 1: FastAPI backend
uvicorn backend.main:app --port 7860 --reload

# Terminal 2: Vite dev server (proxies /api to :7860)
cd frontend && npm run dev
```
App runs on http://localhost:5173 (Vite dev) or http://localhost:7860 (production).

### Run the app (production)
```bash
cd frontend && npm run build
uvicorn backend.main:app --port 7860
```

### Install dependencies
```bash
pip install -r requirements.txt
cd frontend && npm install
```

### Build frontend (required for production)
```bash
cd frontend && npm run build
```

### Docker
```bash
docker build -t train-timetable-plotter .
docker run -p 7860:7860 train-timetable-plotter
```

## Architecture

### Data Flow
```
File upload (.xlsx or .json project)
  → POST /api/upload → parse Excel or restore JSON → store in SessionState
  → GET /api/trains → build grid rows + plot series → JSON response
  → React renders TrainPlot (ECharts) + TrainGrid (AG Grid)
  → user dblclick → EditDialog → POST /api/edit/save → refetch trains → re-render
  → user click (color mode) → PUT /api/colors → update store → re-render
  → GET /api/export/xlsx|circuits|project → download file
```

### Backend (`backend/`)
- **main.py** — FastAPI app factory, CORS, static file serving, API routers
- **config.py** — Port, static path constants
- **deps.py** — `get_state()` dependency injection
- **models/session.py** — `SessionState` dataclass with dict-like interface (so `table_editor.py` and `excel_loader.py` work unchanged)
- **models/requests.py** — Pydantic request bodies
- **models/responses.py** — Pydantic response models
- **routers/upload.py** — `POST /api/upload` (Excel + JSON)
- **routers/sheets.py** — `GET /api/sheets`, `PUT /api/sheets/select`
- **routers/trains.py** — `GET /api/trains` (grid rows + plot series + station items + axis bounds)
- **routers/edit.py** — `POST /api/edit/save`, `POST /api/edit/clear`
- **routers/colors.py** — `PUT /api/colors`, `DELETE /api/colors/all`
- **routers/export.py** — `GET /api/export/xlsx|circuits|project`
- **services/session_store.py** — In-memory singleton session store
- **services/excel_service.py** — Adapter: `excel_loader` → `SessionState`
- **services/export_service.py** — XLSX timetable, vehicle circuits, project JSON builders
- **services/plot_data.py** — Grid rows + plot series construction

### Shared Python Modules (unchanged from original)
- **utils.py** — `parse_time()`, `format_time_decimal()`, `format_time_hhmm()`, `parse_km()`, `apply_midnight_correction()`, `normalize()`, header detection
- **table_editor.py** — `save_cell_time()`, `clear_cell_time()`, `propagate_time_shift()`
- **excel_loader.py** — `read_workbook()`, `extract_excel_data()`, `read_and_store_in_session()`

### Frontend (`frontend/`)
- **src/main.tsx** — React entry point
- **src/App.tsx** — App shell: layout, file upload, sheet selector, all interactions
- **src/api.ts** — Fetch wrapper for all API calls
- **src/store.ts** — Zustand store (sheets, trainColors, selectedSheet, activeColor, etc.)
- **src/types.ts** — TypeScript interfaces matching API responses
- **src/components/TrainPlot.tsx** — ECharts time-vs-km chart (adapted from Streamlit component)
- **src/components/TrainGrid.tsx** — AG Grid timetable (adapted from Streamlit component)
- **src/components/EditDialog.tsx** — Modal for editing time, propagation checkbox
- **src/components/ColorToolbar.tsx** — Color palette buttons
- **src/components/FileUpload.tsx** — Drag & drop file upload
- **src/components/SheetSelector.tsx** — Sheet tab buttons
- **src/components/ExportBar.tsx** — Download buttons
- **src/styles/theme.css** — Warm cream theme

### Session State Keys
- `sheets_data` — List of `{sheet, trains}` where each train record has `train_number`, `station`, `km`, `time` (formatted string), `time_decimal` (float hours), optional `stop_type` ("p"/"o" for dual stations).
- `station_map` / `station_maps` — Station-to-km mapping (reference from first sheet, plus per-sheet maps).
- `train_colors` — Dict mapping train number (str) to hex color (str). Used by both components for line/column coloring.
- `uploaded_hash` — SHA256 hash of uploaded file bytes (prevents re-parsing same file).
- `uploaded_name` — Original filename of uploaded Excel (used for export naming).
- `selected_sheet` — Currently selected sheet name.

### Time Handling
Times are stored as decimal hours (float). Midnight crossing is detected when time difference exceeds 12h. Day offset is tracked via `(+N)` suffix in formatted strings. The parser (`parse_time`) accepts HH:MM, HH:MM:SS, HH.MM, Excel day fractions, and datetime objects.

### JSON Project Format
Projects are saved as JSON with `_format: "train-timetable-plotter-project"` and `_version: 1`. Contains: `sheets_data`, `station_map`, `station_maps`, `train_colors`, `uploaded_name`, `selected_sheet`. Loading validates the `_format` field and restores all session state keys directly.

### API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/upload` | Upload .xlsx/.json |
| GET | `/api/sheets` | List sheets |
| PUT | `/api/sheets/select` | Select sheet |
| GET | `/api/trains` | Grid rows + plot series |
| POST | `/api/edit/save` | Save time (+ optional propagation) |
| POST | `/api/edit/clear` | Clear stop |
| PUT | `/api/colors` | Set train color |
| DELETE | `/api/colors/all` | Reset all colors |
| GET | `/api/export/xlsx` | Download timetable XLSX |
| GET | `/api/export/circuits` | Download vehicle circuits XLSX |
| GET | `/api/export/project` | Download project JSON |
| GET | `/api/example` | Download example file |
