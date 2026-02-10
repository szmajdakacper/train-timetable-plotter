# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Train Timetable Plotter is a Streamlit web app for visualizing and editing train timetables from Excel files. It uses two custom Streamlit components built with React/TypeScript (Vite): an AG Grid table and an ECharts time-vs-km plot. The UI and comments are largely in Polish.

## Commands

### Run the app
```bash
streamlit run app.py
```
App runs on http://localhost:8501.

### Install Python dependencies
```bash
pip install -r requirements.txt
```

### Build frontend components (required after frontend changes)
```bash
cd train_grid_component/frontend && npm install && npm run build && cd ../..
cd train_plot_component/frontend && npm install && npm run build && cd ../..
```

### Frontend dev mode (hot reload)
Run the Vite dev servers alongside Streamlit:
```bash
# Terminal 1: Grid component dev server (port 5173)
cd train_grid_component/frontend && npm run dev

# Terminal 2: Plot component dev server (port 5174)
cd train_plot_component/frontend && npm run dev

# Terminal 3: Streamlit with dev flags
TRAIN_GRID_DEV=1 TRAIN_PLOT_DEV=1 streamlit run app.py
```
When `TRAIN_GRID_DEV=1` or `TRAIN_PLOT_DEV=1` is set, the Python backend connects to localhost Vite servers instead of loading from the committed `dist/` folders.

## Architecture

### Data Flow
```
Excel upload → read_workbook() (expand merged cells) → extract_excel_data()
  → parse headers, stations, trains → store in st.session_state
  → render plot (train_plot_component) + grid (train_grid_component)
  → user clicks cell/point → color mode: assign color | normal mode: modal dialog
  → save_cell_time() → optional propagate_time_shift()
  → update session_state → st.rerun()
  → export to XLSX
```

### Python Modules
- **app.py** — Main Streamlit entry point. Handles file upload, sheet selection, rendering both components, edit dialogs, color tool, and XLSX export. All UI state lives in `st.session_state`.
- **excel_loader.py** — Reads Excel workbooks via openpyxl, expands merged cells, detects headers, extracts station maps and train data per sheet, validates cross-sheet consistency.
- **table_editor.py** — Time editing operations: `save_cell_time()`, `clear_cell_time()`, `propagate_time_shift()` (cascades a time delta to downstream stations by km).
- **utils.py** — Parsing utilities: `parse_time()` (handles HH:MM, HH.MM, Excel fractions, day suffixes like `(+1)`), `format_time_decimal()`, `format_time_hhmm()`, `parse_km()`, `apply_midnight_correction()`, `normalize()` (Polish-aware text normalization with accent stripping), header detection (`find_headers()`, `extract_stations()`, `extract_train_columns()`).

### Custom Streamlit Components
Each component follows the same pattern: a Python backend in `backend/` that declares the component and a React/TypeScript frontend in `frontend/` built with Vite.

- **train_grid_component** — AG Grid wrapper. Sends `cellDoubleClick` (edit mode), `cellClick` (color mode), and `cellValueChanged` (inline edit) events back to Streamlit. Port 5173 in dev mode.
- **train_plot_component** — ECharts line chart (time x-axis, km y-axis). Sends `pointDoubleClick` (edit mode) and `pointClick` (color mode) events back to Streamlit. Port 5174 in dev mode.

Both components' `dist/` folders are committed to the repo so the app can deploy on Streamlit Cloud without Node.js.

### Session State Keys
- `sheets_data` — List of `{sheet, trains}` where each train record has `train_number`, `station`, `km`, `time` (formatted string), `time_decimal` (float hours), optional `stop_type` ("p"/"o" for dual stations).
- `station_map` / `station_maps` — Station-to-km mapping (reference from first sheet, plus per-sheet maps).
- `plot_nonce_*` / `grid_nonce_*` — Incremented to force component re-render after edits.
- `train_colors` — Dict mapping train number (str) to hex color (str). Used by both components for line/column coloring.
- `active_color` — Currently selected color hex in color tool mode, or `None` when color tool is inactive.
- `uploaded_hash` — SHA256 hash of uploaded file bytes (prevents re-parsing same file).
- `uploaded_name` — Original filename of uploaded Excel (used for export naming).
- `selected_sheet` — Currently selected sheet name.
- `station_check` — Cross-sheet station consistency check result `{ok: bool, mismatches: list}`.

### Time Handling
Times are stored as decimal hours (float). Midnight crossing is detected when time difference exceeds 12h. Day offset is tracked via `(+N)` suffix in formatted strings. The parser (`parse_time`) accepts HH:MM, HH:MM:SS, HH.MM, Excel day fractions, and datetime objects.

### Header Detection
Excel headers are matched using normalized Polish variants (e.g., "numer pociagu", "nr pociagu", "ze stacji", "do stacji", "km"). Normalization strips accents, lowercases, and collapses whitespace.
