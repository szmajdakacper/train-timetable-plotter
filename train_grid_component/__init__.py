import os
import streamlit.components.v1 as components
from pathlib import Path

# Tryb deweloperski (jeśli frontend odpalasz np. `npm run dev`)
# wtedy podajesz URL np. "http://localhost:3000"
# ale w normalnym trybie (production) ładujesz pliki z dist
_component_func = components.declare_component(
    "train_grid_component",
    path=str(Path(__file__).parent / "frontend" / "dist")
)

def train_grid(data, key=None):
    """Wrapper do wywołania komponentu w Streamlit"""
    return _component_func(data=data, key=key)