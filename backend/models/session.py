from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionState:
    """Dict-like session state so table_editor.py and excel_loader.py work unchanged."""

    _data: dict[str, Any] = field(default_factory=dict)

    # --- dict protocol used by table_editor / excel_loader ---

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def setdefault(self, key: str, default: Any = None) -> Any:
        return self._data.setdefault(key, default)

    # --- convenience ---

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)
