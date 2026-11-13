"""Rescue pets that need a foster home, from the RescueGroups.org API v5.

Official API, free public key: https://rescuegroups.org/services/adoptable-pet-data-api/
Set the key as the RESCUEGROUPS_API_KEY secret. Without it this source is skipped.
Docs: https://api.rescuegroups.org/v5/public/docs
"""
from __future__ import annotations

import html
import os
import re

from .. import geo, http

SOURCE_ID = "rescue"
LABEL = "Rescue pets needing a foster"
API = "https://api.rescuegroups.org/v5/public/animals/search/available/{species}/"
SIZE = {"Small": "small", "Medium": "medium", "Large": "large", "X-Large": "large"}
AGE = {"Baby": "young", "Young": "young", "Adult": "adult", "Senior": "senior"}


def temperament(attrs: dict) -> list[str]:
    tags = []
    if attrs.get("energyLevel") == "Low" or attrs.get("activityLevel") in ("Not Active", "Slightly Active"):
        tags.append("calm")
    if attrs.get("energyLevel") == "High" or attrs.get("activityLevel") == "Highly Active":
        tags.append("energetic")
    if attrs.get("newPeopleReaction") == "Friendly":
        tags.append("friendly")
    training = (attrs.get("obedienceTraining") or "").lower()
    if "basic training" in training or "well trained" in training:
        tags.append("trained")
    return tags


def to_listing(animal: dict, species: str, included: dict) -> dict:
    attrs = animal.get("attributes", {})
    org = {}
    for ref in animal.get("relationships", {}).get("orgs", {}).get("data", []):
        org = included.get(("orgs", ref.get("id")), {})
    zip_code = str(org.get("postalcode") or "")[:5]
    # First sentence only: rescue write-ups often go on to describe how the animal was found.
    description = " ".join(html.unescape(attrs.get("descriptionText") or "").replace("\xa0", " ").split())
    description = re.split(r"(?<=[.!?])\s", description, maxsplit=1)[0]
    listing = {
        "id": f"rescue-{animal.get('id')}",
        "src": SOURCE_ID,
        "title": attrs.get("name") or "Unnamed",
        "petName": attrs.get("name") or "",
        "breed": attrs.get("breedString") or "",
        "org": org.get("name") or "Rescue group",
        "kind": "rescue",
        "species": [species],
        "size": [SIZE[attrs["sizeGroup"]]] if attrs.get("sizeGroup") in SIZE else (["any"] if species == "cat" else []),
        "temper": temperament(attrs),
        "age": [AGE[attrs["ageGroup"]]] if attrs.get("ageGroup") in AGE else [],
        "activity": ["foster"],
        "hood": org.get("city") or "",
        "borough": (geo.borough_for_zip(zip_code) if zip_code else "") or org.get("state") or "",
        "says": (description[:160].rsplit(" ", 1)[0] + "…") if len(description) > 160 else description,
        "when": "",
        "days": ["weekday", "weekend"],
        "daypart": ["any"],
        "commit": "flexible",
        "commitNote": "Foster until adopted, or as agreed with the rescue",
        "requires": ["application"],
        "prep": "Foster application with the rescue",
        "cost": "free",
        "costNote": "Free; rescues usually cover vet care",
        "startRank": 3,
        "status": "open",
        "url": attrs.get("url") or org.get("url") or "",
        "cta": "See this pet",
        "photo": attrs.get("pictureThumbnailUrl") or "",
        "source": "RescueGroups.org",
        "sourceUpdated": (attrs.get("updatedDate") or "")[:10],
    }
    latlon = geo.zip_to_latlon(zip_code) if zip_code else None
    if latlon:
        listing["lat"], listing["lon"] = latlon
    return listing


def parse_response(payload: dict, species: str) -> list[dict]:
    included = {(inc.get("type"), inc.get("id")): inc.get("attributes", {}) for inc in payload.get("included", [])}
    return [to_listing(animal, species, included) for animal in payload.get("data", [])]


def spread(listings: list[dict], per_org: int, total: int) -> list[dict]:
    """Keep the nearest pets but no more than `per_org` from one rescue, so one big group cannot fill the page."""
    seen: dict[str, int] = {}
    kept = []
    for listing in listings:  # already nearest-first
        seen[listing["org"]] = seen.get(listing["org"], 0) + 1
        if seen[listing["org"]] <= per_org:
            kept.append(listing)
    return kept[:total]


def fetch(config: dict) -> list[dict] | None:
    key = os.environ.get("RESCUEGROUPS_API_KEY", "").strip()
    if not key:
        return None  # not configured: skipped, not an error
    cfg = config["rescuegroups"]
    home = config["home"]
    body = {"data": {
        "filters": [{"fieldName": "animals.isNeedingFoster", "operation": "equals", "criteria": True}],
        "filterRadius": {"miles": cfg["miles"], "coordinates": f"{home['lat']},{home['lon']}"},
    }}
    headers = {"Authorization": key, "Content-Type": "application/vnd.api+json"}
    listings: list[dict] = []
    for species_path, species in (("dogs", "dog"), ("cats", "cat")):
        url = API.format(species=species_path) + f"?limit={cfg['fetchLimit']}&include=orgs&sort=animals.distance"
        payload = http.fetch_json(url, data=body, headers=headers)
        listings += spread(parse_response(payload, species), cfg["perOrg"], cfg["perSpecies"])
    return listings
