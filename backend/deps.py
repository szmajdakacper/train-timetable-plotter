from backend.models.session import SessionState
from backend.services.session_store import get_session


def get_state() -> SessionState:
    return get_session()
