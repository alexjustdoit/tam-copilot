"""
Taxonomy loader/saver. taxonomy.json is the source of truth — it grows as users add new tags/categories.
"""
from __future__ import annotations

import json
from pathlib import Path

TAXONOMY_PATH = Path(__file__).parent / "taxonomy.json"


def load_taxonomy() -> dict:
    """Returns {"tags": [...], "categories": [...]}."""
    return json.loads(TAXONOMY_PATH.read_text())


def save_taxonomy(taxonomy: dict) -> None:
    TAXONOMY_PATH.write_text(json.dumps(taxonomy, indent=2))
