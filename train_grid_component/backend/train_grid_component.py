from pathlib import Path
import os
import streamlit.components.v1 as components


_USE_DEV = bool(os.environ.get("TRAIN_GRID_DEV"))

if _USE_DEV:
    _component_func = components.declare_component(
        "train_grid",
        url="http://localhost:5173",
    )
else:
    build_dir = (Path(__file__).parent.parent / "frontend" / "dist").resolve()
    _component_func = components.declare_component(
        "train_grid",
        path=str(build_dir),
    )


def train_grid(row_data, column_defs, key=None, height=400, theme="ag-theme-alpine",
               train_colors=None, color_mode=False):
    """
    Wyświetla siatkę AG Grid jako komponent Streamlit i zwraca zdarzenia.

    Args:
        row_data: list[dict]
        column_defs: list[dict]
        key: dowolny klucz unikalny w obrębie strony
        height: wysokość w px
        theme: klasa motywu AG Grid (np. "ag-theme-alpine")
        train_colors: dict mapping train_number -> hex color
        color_mode: bool — when True, single clicks send cellClick events

    Returns:
        dict | None: np. {"type": "cellDoubleClick", "field": str, "row": dict}
    """
    return _component_func(
        rowData=row_data,
        columnDefs=column_defs,
        height=height,
        theme=theme,
        trainColors=train_colors or {},
        colorMode=color_mode,
        key=key,
        default=None,
    )


