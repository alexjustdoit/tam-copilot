"""
Taxonomy loader/saver. taxonomy.json is the source of truth — it grows as users add new tags/categories.
"""
from __future__ import annotations

import json
from pathlib import Path

TAXONOMY_PATH = Path(__file__).parent / "taxonomy.json"


def _get_taxonomy_path() -> Path:
    from config import SCC_MODE
    if not SCC_MODE:
        return TAXONOMY_PATH
    from data.session_store import get_fixtures_dir
    return get_fixtures_dir() / "taxonomy.json"


def load_taxonomy() -> dict:
    """Returns {"tags": [...], "categories": [...]}."""
    return json.loads(_get_taxonomy_path().read_text())


def save_taxonomy(taxonomy: dict) -> None:
    _get_taxonomy_path().write_text(json.dumps(taxonomy, indent=2))
