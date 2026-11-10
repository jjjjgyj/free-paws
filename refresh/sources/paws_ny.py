"""PAWS NY neighbor-pet listings, read from their public pages on Points of Light Engage.

There is no free API for these posts, so this reads the organization's index
page plus each listing page (about 20 small requests per run, one per second).
robots.txt allows these paths. If the site's HTML changes, parse_index or
parse_listing is the place to fix; tests/test_paws_ny.py shows what they expect.
"""
from __future__ import annotations

import html as html_lib
import re

from .. import geo, http, tagging

SOURCE_ID = "paws"
LABEL = "PAWS NY neighbor pets"

BOILERPLATE_STARTS = ("If you enjoy spending time", "In order to begin", "We're currently offering", "Check out")
STOP_LINES = ("Additional Volunteer Opportunities", "Posted with", "Issue area")


def parse_index(page: str) -> list[str]:
    """Listing URLs on the organization page, in page order, without duplicates."""
    urls = re.findall(r'href="(https://engage\.pointsoflight\.org/opportunities/[0-9a-f-]+)"', page)
    return list(dict.fromkeys(urls))


def _lines(page: str) -> list[str]:
    main = re.search(r"<main.*?</main>", page, re.S)
    text = main.group(0) if main else page
    text = re.sub(r"<(script|style|svg|form).*?</\1>", "", text, flags=re.S)
    text = html_lib.unescape(re.sub(r"<[^>]+>", "\n", text))
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n")]
    out: list[str] = []
    for ln in lines:
        if ln and ln not in out:  # the page repeats blocks for mobile and desktop
            out.append(ln)
    return out


def _between(lines: list[str], start: str, stops: tuple[str, ...]) -> list[str]:
    try:
        i = next(n for n, ln in enumerate(lines) if ln.startswith(start))
    except StopIteration:
        return []
    out = []
    for ln in lines[i + 1:]:
        if ln.startswith(stops) or re.match(r"\d+ shifts? available", ln):
            break
        out.append(ln)
    return out


def _pet_name(title: str, pet_text: str) -> str:
    m = re.search(r"Meet ([A-Z][\w']+(?: and [A-Z][\w']+)?)\s*!", pet_text)
    if m:
        return m.group(1)
    m = re.search(r"named ([A-Z][\w']+)", title) or re.search(r"\b(?:dog|cat|siblings),? ([A-Z][\w']+(?: and [A-Z][\w']+)?)\s*!", title)
    return m.group(1) if m else ""


def _excerpt(sentences: list[str], limit: int = 220) -> str:
    text = " ".join(sentences).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(". ", 1)[0]
    return (cut if len(cut) > 60 else text[:limit].rsplit(" ", 1)[0]) .rstrip(".") + "."


def parse_listing(page: str, url: str) -> dict | None:
    """One listing page -> one listing dict, or None if the page is not an open listing."""
    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    if not title_m:
        return None
    title = html_lib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title_m.group(1)))).strip()
    lines = _lines(page)
    if "Recruiting now" not in lines:
        return None

    address = next((ln for ln in lines if re.search(r",\s*NY\s+\d{5}\b", ln)), "")
    zip_m = re.search(r"\b(\d{5})\b\s*$", address)
    zip_code = zip_m.group(1) if zip_m else ""
    hood = re.sub(r",\s*NY\s+\d{5}\s*$", "", address)

    about = _between(lines, "About this Opportunity", STOP_LINES)
    pet_lines = []
    for ln in about:
        if ln.startswith(BOILERPLATE_STARTS):
            break
        pet_lines.append(ln)
    pet_text = " ".join(pet_lines)
    # Keep only sentences about the pet: the posts also describe the guardian's
    # health, which the site has no reason to repeat.
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(
        ln for ln in pet_lines if not ln.startswith(("Meet ", "We are looking for volunteers"))))
    described = [s for s in sentences if s and not re.search(r"guardian|owner|\b(?:his|her|their) (?:mom|dad|human)", s, re.I)]

    shift_i = next((n for n, ln in enumerate(lines) if re.match(r"\d+ shifts? available", ln)), None)
    shifts = []
    if shift_i is not None:
        for ln in lines[shift_i + 1:]:
            if ln.startswith(STOP_LINES):
                break
            shifts.append(ln)
    shift_text = "; ".join(shifts)
    days, dayparts = tagging.schedule_tags(shift_text)

    subject = f"{title} {pet_text}"
    breed, sizes = tagging.breeds_in(subject)
    species = tagging.species_in(subject)
    pet_name = _pet_name(title, pet_text)
    is_general = not pet_text or title.lower().startswith("help seniors")
    activity = ["walk"] if "dog" in species and "walk" in subject.lower() else []
    if "cat" in species or re.search(r"feed|litter|cat care", subject, re.I):
        activity.append("visit")
    if is_general:
        species, activity = ["dog", "cat"], ["walk", "visit"]

    updated_m = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})', page)
    latlon = geo.zip_to_latlon(zip_code) if zip_code else None

    listing = {
        "id": "paws-" + url.rstrip("/").rsplit("-", 1)[-1],
        "src": SOURCE_ID,
        "title": "Join the PAWS NY visitor pool" if is_general else (pet_name or title.rstrip("!").strip()),
        "petName": pet_name,
        "breed": breed,
        "org": "PAWS NY",
        "kind": "neighbor",
        "species": species,
        "size": ["any"] if is_general or species == ["cat"] else sizes,
        "temper": [] if is_general else tagging.temperament_in(" ".join(described)),
        "age": ["any"] if is_general else (tagging.ages_in(f"{title} {' '.join(described)}") or (["adult"] if pet_name else [])),
        "activity": activity or ["visit"],
        "hood": hood,
        "borough": geo.borough_for_zip(zip_code) if zip_code else "",
        "says": "After orientation you pick open shifts close to home." if is_general else _excerpt(described),
        "when": tagging.friendly_times(shift_text),
        "days": days,
        "daypart": dayparts,
        "commit": "weekly",
        "commitNote": "One 30 to 60 minute visit a week; PAWS NY asks for about 6 months",
        "requires": ["orientation"],
        "prep": "One-hour virtual orientation, 18+, proof of COVID-19 vaccination. Dates at pawsny.org/volunteer",
        "cost": "free",
        "costNote": "Free",
        "startRank": 3,
        "status": "open",
        "url": url,
        "source": "via Points of Light",
        "sourceUpdated": updated_m.group(1) if updated_m else "",
    }
    if latlon:
        listing["lat"], listing["lon"] = latlon
    return listing


def fetch(config: dict) -> list[dict]:
    index_url = config["paws"]["indexUrl"]
    listings, seen_titles = [], set()
    for url in parse_index(http.fetch(index_url)):
        listing = parse_listing(http.fetch(url), url)
        if not listing:
            continue
        key = (listing["title"], listing["hood"])
        if key in seen_titles:  # PAWS NY posts its general call more than once
            continue
        seen_titles.add(key)
        listings.append(listing)
    return listings
