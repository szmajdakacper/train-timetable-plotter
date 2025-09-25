from pathlib import Path
import os
import streamlit.components.v1 as components


_USE_DEV = bool(os.environ.get("TRAIN_PLOT_DEV"))

if _USE_DEV:
    _component_func = components.declare_component(
        "train_plot",
        url="http://localhost:5174",
    )
else:
    build_dir = (Path(__file__).parent.parent / "frontend" / "dist").resolve()
    _component_func = components.declare_component(
        "train_plot",
        path=str(build_dir),
    )


def train_plot(y_stations, series, x_min_ms=None, x_max_ms=None, key=None, height=420):
    """
    Renderuje wykres tras pociągów (ECharts).

    Args:
        y_stations: list[dict] - [{"name": str, "km": float}] (oś Y w km, z etykietami stacji)
        series: list[dict] - np. [{"name": "123", "points": [[ms, km], ...]}]
        x_min_ms: int | None - minimalny czas w ms (oś X)
        x_max_ms: int | None - maksymalny czas w ms (oś X)
        key: unikalny klucz komponentu
        height: wysokość w px

    Returns: None | dict (np. eventy kliknięć w przyszłości)
    """
    return _component_func(
        yStations=y_stations,
        series=series,
        xMinMs=x_min_ms,
        xMaxMs=x_max_ms,
        height=height,
        key=key,
        default=None,
    )


