"""Turn free-text listing descriptions into the filter tags the site uses.

Everything here is plain keyword rules: no AI, no network. To teach the site a
new breed or a new temperament word, add a line to the tables below.
"""
from __future__ import annotations

import re

# (pattern, display name, typical sizes). First match wins per position, so put
# longer names before shorter ones that they contain.
BREEDS: list[tuple[str, str, list[str]]] = [
    (r"golden lab", "Golden lab mix", ["large"]),
    (r"black lab|labrador|\blab\b", "Labrador", ["large"]),
    (r"golden retriever|retriever", "Retriever", ["large"]),
    (r"husky", "Siberian husky", ["large"]),
    (r"german shepherd|shepherd", "Shepherd", ["large"]),
    (r"great dane", "Great Dane", ["large"]),
    (r"pit ?bull|pittie|staff(?:y|ordshire)", "Pit bull", ["medium", "large"]),
    (r"chow", "Chow", ["medium", "large"]),
    (r"boxer", "Boxer", ["medium", "large"]),
    (r"basset", "Basset hound", ["medium"]),
    (r"beagle", "Beagle", ["medium"]),
    (r"bulldog", "Bulldog", ["medium"]),
    (r"cocker|spaniel", "Spaniel", ["medium"]),
    (r"corgi", "Corgi", ["medium"]),
    (r"poodle", "Poodle", ["medium"]),
    (r"cavapoo", "Cavapoo", ["small"]),
    (r"chihuahua", "Chihuahua", ["small"]),
    (r"dachshund", "Dachshund", ["small"]),
    (r"bichon", "Bichon", ["small"]),
    (r"yorkie|yorkshire", "Yorkie", ["small"]),
    (r"maltese", "Maltese", ["small"]),
    (r"shih ?tzu", "Shih Tzu", ["small"]),
    (r"pomeranian", "Pomeranian", ["small"]),
    (r"\bpug\b", "Pug", ["small"]),
    (r"terrier", "Terrier", []),
    (r"guide dog", "Guide dog", ["large"]),
    (r"domestic (?:short|medium|long) ?hair", "Domestic shorthair", []),
]

TEMPERAMENT: dict[str, str] = {
    "gentle": r"gentle|mellow|easy ?going",
    "calm": r"\bcalm|laid[- ]back|relaxed|quiet|low[- ]energy",
    "affectionate": r"affectionate|loving|cuddl|sweet|snuggl",
    "friendly": r"friendly|social\b|outgoing|loves people",
    "energetic": r"energetic|excitement|excitable|playful|enthusias|joyful|more exercise|high[- ]energy|very active",
    "trained": r"well[- ]trained|well[- ]behaved|house ?trained|service dog|guide dog",
}

DAY_WORDS = {
    "mon": "weekday", "tue": "weekday", "wed": "weekday", "thu": "weekday", "fri": "weekday",
    "sat": "weekend", "sun": "weekend",
}


def breeds_in(text: str) -> tuple[str, list[str]]:
    """Return ("Siberian husky and Retriever", ["large"]) for the breeds named in `text`."""
    low = text.lower()
    found: list[tuple[int, str, list[str]]] = []
    taken: list[range] = []
    for pattern, name, sizes in BREEDS:
        for m in re.finditer(pattern, low):
            if any(m.start() in r or m.end() - 1 in r for r in taken):
                continue
            taken.append(range(m.start(), m.end()))
            if name not in [f[1] for f in found]:
                found.append((m.start(), name, sizes))
    found.sort()
    sizes: list[str] = []
    for _, _, s in found:
        sizes += [x for x in s if x not in sizes]
    return " and ".join(name for _, name, _ in found), sizes


def temperament_in(text: str) -> list[str]:
    low = text.lower()
    return [tag for tag, pattern in TEMPERAMENT.items() if re.search(pattern, low)]


def ages_in(text: str) -> list[str]:
    low = text.lower()
    ages: list[str] = []
    if re.search(r"puppy|kitten", low):
        ages.append("young")
    if re.search(r"\bsenior\b|elderly (?:dog|cat)", low):
        ages.append("senior")
    stated = []
    for m in re.finditer(r"(\d{1,2})[- ]year[- ]old", low):
        years = int(m.group(1))
        tag = "young" if years < 2 else "senior" if years >= 9 else "adult"
        if tag not in stated:
            stated.append(tag)
    return stated or ages  # an explicit age beats a loose word like "senior"


def species_in(text: str) -> list[str]:
    low = text.lower()
    species = []
    if re.search(r"\bdogs?\b|\bpupp|walk", low) or breeds_in(low)[1]:
        species.append("dog")
    if re.search(r"\bcats?\b|kitten|litter|shorthair", low):
        species.append("cat")
    return species


def schedule_tags(shift_text: str) -> tuple[list[str], list[str]]:
    """("Mon, Wed, Fri: 11:30 to 14:00 EST") -> (["weekday"], ["midday"])."""
    low = shift_text.lower()
    days = []
    if "daily" in low or "every day" in low:
        days = ["weekday", "weekend"]
    for word, kind in DAY_WORDS.items():
        if re.search(rf"\b{word}", low) and kind not in days:
            days.append(kind)
    dayparts: list[str] = []
    for m in re.finditer(r"(\d{1,2}):(\d{2})\s*to\s*(\d{1,2}):(\d{2})", low):
        start = int(m.group(1)) + int(m.group(2)) / 60
        end = int(m.group(3)) + int(m.group(4)) / 60
        if start < 11:
            dayparts.append("morning")
        if start < 16 and end > 11:
            dayparts.append("midday")
        if end > 16:
            dayparts.append("evening")
    dayparts = [d for d in ("morning", "midday", "evening") if d in dayparts]
    return (days or ["weekday", "weekend"]), (dayparts or ["any"])


def friendly_times(shift_text: str) -> str:
    """Rewrite 24-hour ranges as 10am to 7pm and drop the timezone suffix."""
    def clock(h: str, m: str) -> str:
        hour = int(h)
        suffix = "am" if hour < 12 else "pm"
        hour = hour % 12 or 12
        return f"{hour}{'' if m == '00' else ':' + m}{suffix}"

    text = re.sub(r"(\d{1,2}):(\d{2})\s*to\s*(\d{1,2}):(\d{2})",
                  lambda m: f"{clock(m.group(1), m.group(2))} to {clock(m.group(3), m.group(4))}", shift_text)
    return re.sub(r"\s*\b(EST|EDT|ET)\b", "", text).strip()
