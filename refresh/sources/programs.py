"""Stable programs (shelters, day trips, cat cafes) kept by hand in data/programs.json."""
from __future__ import annotations

import json
from pathlib import Path

SOURCE_ID = "programs"
LABEL = "Hand-kept programs"
PATH = Path(__file__).resolve().parent.parent.parent / "data" / "programs.json"


def fetch(config: dict) -> list[dict]:
    listings = json.loads(PATH.read_text())
    for listing in listings:
        listing["src"] = SOURCE_ID
        listing.setdefault("status", "open")
    return listings
