"""Each source module exposes SOURCE_ID, LABEL and fetch(config) -> list of listings.

fetch returns None when the source is not configured (for example, no API key).
To add a source, write a module with those three names and add it to ALL.
The Idealist Listings API would slot in here once Idealist grants access.
"""
from . import paws_ny, programs, rescuegroups

ALL = [paws_ny, rescuegroups, programs]
