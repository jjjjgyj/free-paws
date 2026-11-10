"""Rebuild site/data/listings.json and site/data/status.json.  Run: python -m refresh

If one source fails, its previous listings are kept and the failure is recorded
in status.json so the site can say so. The run fails only when nothing loaded.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import geo
from .sources import ALL

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "data" / "config.json"
LISTINGS = ROOT / "site" / "data" / "listings.json"
STATUS = ROOT / "site" / "data" / "status.json"


def main() -> int:
    config = json.loads(CONFIG.read_text())
    previous = json.loads(LISTINGS.read_text()) if LISTINGS.exists() else []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    listings: list[dict] = []
    report = []

    for source in ALL:
        kept = [x for x in previous if x.get("src") == source.SOURCE_ID]
        entry = {"id": source.SOURCE_ID, "label": source.LABEL, "ok": True, "stale": False, "message": ""}
        try:
            fresh = source.fetch(config)
            if fresh is None:
                entry.update(ok=False, message="not set up yet")
                fresh = []
            elif not fresh and kept:
                raise RuntimeError("returned no listings; the source may have changed")
            else:
                for x in fresh:
                    x["firstSeen"] = next((p.get("firstSeen") for p in kept if p["id"] == x["id"]), None) or today
        except Exception as err:  # keep yesterday's data rather than show nothing
            print(f"[{source.SOURCE_ID}] FAILED: {err}", file=sys.stderr)
            entry.update(ok=False, stale=bool(kept), message=str(err)[:200])
            fresh = kept
        entry["count"] = len(fresh)
        print(f"[{source.SOURCE_ID}] {len(fresh)} listings{' (kept from last run)' if entry['stale'] else ''}")
        listings += fresh
        report.append(entry)

    geo.save()
    listings.sort(key=lambda x: x["id"])
    LISTINGS.parent.mkdir(parents=True, exist_ok=True)
    LISTINGS.write_text(json.dumps(listings, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    STATUS.write_text(json.dumps({
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": report,
    }, indent=1) + "\n")
    return 0 if listings else 1


if __name__ == "__main__":
    sys.exit(main())
