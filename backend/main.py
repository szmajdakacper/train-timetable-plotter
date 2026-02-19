import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import STATIC_DIR
from backend.routers import upload, sheets, trains, edit, colors, export

app = FastAPI(title="Train Timetable Plotter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(upload.router)
app.include_router(sheets.router)
app.include_router(trains.router)
app.include_router(edit.router)
app.include_router(colors.router)
app.include_router(export.router)

# Serve example file
EXAMPLE_FILE = Path(__file__).resolve().parent.parent / "example_table" / "d1_test.xlsx"


@app.get("/api/example")
async def download_example() -> FileResponse:
    return FileResponse(
        EXAMPLE_FILE,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="d1_test.xlsx",
    )


# Serve React SPA static files (production)
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))
