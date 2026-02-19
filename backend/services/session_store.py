from __future__ import annotations

from backend.models.session import SessionState

# Single global session (single-user app, like the Streamlit version).
_session = SessionState()


def get_session() -> SessionState:
    return _session


def reset_session() -> SessionState:
    global _session
    _session = SessionState()
    return _session
