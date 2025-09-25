"""Public API for the train_grid_component package.

Allows convenient imports:
    from train_grid_component import train_grid
"""

from .backend.train_grid_component import train_grid  # re-export

__all__ = ["train_grid"]
