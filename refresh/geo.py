"""ZIP code -> coordinates, cached in data/zipcache.json so each ZIP is looked up once, ever."""
from __future__ import annotations

import json
from pathlib import Path

from . import http

CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "zipcache.json"
LOOKUP_URL = "https://api.zippopotam.us/us/{zip}"

_cache: dict[str, list[float] | None] | None = None
_dirty = False


def _load() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}
    return _cache


def zip_to_latlon(zip_code: str) -> tuple[float, float] | None:
    """Center of a US ZIP code, or None if it cannot be resolved."""
    global _dirty
    cache = _load()
    if zip_code not in cache:
        try:
            place = http.fetch_json(LOOKUP_URL.format(zip=zip_code))["places"][0]
            cache[zip_code] = [round(float(place["latitude"]), 4), round(float(place["longitude"]), 4)]
        except Exception:
            return None  # not cached, so the next run tries again
        _dirty = True
    hit = cache[zip_code]
    return (hit[0], hit[1]) if hit else None


def save() -> None:
    global _dirty
    if _dirty and _cache is not None:
        CACHE_PATH.write_text(json.dumps(_cache, indent=1, sort_keys=True) + "\n")
        _dirty = False


def borough_for_zip(zip_code: str) -> str:
    prefix = zip_code[:3]
    if prefix in ("100", "101", "102"):
        return "Manhattan"
    if prefix == "103":
        return "Staten Island"
    if prefix == "104":
        return "Bronx"
    if prefix == "112":
        return "Brooklyn"
    if prefix in ("110", "111", "113", "114", "116"):
        return "Queens"
    return ""
