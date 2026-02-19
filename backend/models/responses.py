from __future__ import annotations

from pydantic import BaseModel


class StationItem(BaseModel):
    name: str
    km: float


class PlotPoint(BaseModel):
    value: list[float]  # [ms, km]
    station: str
    train: str
    sheet: str


class PlotSeries(BaseModel):
    name: str
    points: list[PlotPoint]


class GridRow(BaseModel):
    km: str
    stacja: str
    _station_raw: str
    _stop_type: str | None
    times: dict[str, str]  # train_number -> display time


class TrainsResponse(BaseModel):
    grid_rows: list[dict]
    column_defs: list[dict]
    plot_series: list[dict]
    station_items: list[dict]
    x_min_ms: int
    x_max_ms: int
    train_colors: dict[str, str]
    selected_sheet: str


class SheetsResponse(BaseModel):
    sheets: list[str]
    selected_sheet: str


class UploadResponse(BaseModel):
    ok: bool
    sheets: list[str]
    selected_sheet: str
    message: str = ""
