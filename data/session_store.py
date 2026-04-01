"""
Per-session data isolation for Streamlit Community Cloud.

When SCC_MODE=true, each browser session gets its own copy of the fixture data
in data/sessions/{token}/. Stock fixtures are copied on first access and never
modified — so reset means deleting the session directory.

In local/non-SCC mode, get_fixtures_dir() returns the shared fixtures directory
and no session management occurs.
"""
from __future__ import annotations

import shutil
from pathlib import Path

STOCK_FIXTURES_DIR = Path(__file__).parent / "fixtures"
STOCK_TAXONOMY = Path(__file__).parent / "taxonomy.json"
SESSIONS_DIR = Path(__file__).parent / "sessions"


def get_fixtures_dir() -> Path:
    """Return the fixture directory for the current session."""
    from config import SCC_MODE
    if not SCC_MODE:
        return STOCK_FIXTURES_DIR

    import uuid
    import streamlit as st

    if "token" not in st.query_params:
        st.query_params["token"] = str(uuid.uuid4())

    session_dir = SESSIONS_DIR / st.query_params["token"]
    if not session_dir.exists():
        _init_session(session_dir)
    return session_dir


def _init_session(session_dir: Path) -> None:
    """Copy stock fixtures and taxonomy into a fresh session directory."""
    session_dir.mkdir(parents=True, exist_ok=True)
    for src in STOCK_FIXTURES_DIR.glob("*.json"):
        shutil.copy2(src, session_dir / src.name)
    if STOCK_TAXONOMY.exists():
        shutil.copy2(STOCK_TAXONOMY, session_dir / "taxonomy.json")


def reset_session() -> None:
    """Delete session data, clear token, and wipe Streamlit state."""
    import streamlit as st

    if "token" in st.query_params:
        session_dir = SESSIONS_DIR / st.query_params["token"]
        if session_dir.exists():
            shutil.rmtree(session_dir)
        del st.query_params["token"]

    st.session_state.clear()
    st.cache_data.clear()
