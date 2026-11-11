# Free Paws

A public, volunteer-run site that gathers open requests from New Yorkers,
shelters and rescues who need a hand with a dog or cat: walks for neighbors who
can't manage them, cat visits, shelter shifts and foster homes. It has search,
filters, categories and a map. It is independent of the organizations listed.

The listings refresh themselves once a day. No AI is involved in a refresh: a
short Python script (standard library only) fetches each source, tags the
listings with keyword rules, and writes one JSON file that the page reads.

## How it works

```
.github/workflows/refresh.yml   daily job: test, refresh, commit if changed, publish
refresh/                        the refresh script (python -m refresh)
  sources/paws_ny.py            PAWS NY neighbor pets, read from public listing pages
  sources/rescuegroups.py       rescue pets needing a foster, RescueGroups.org API v5
  sources/programs.py           hand-kept programs from data/programs.json
  tagging.py                    breed -> size, words -> temperament, shift text -> days and times
  geo.py                        ZIP -> coordinates, cached in data/zipcache.json
data/config.json                home location, search radius, source URLs
data/programs.json              shelters, day trips, cat cafes: edit by hand
site/index.html                 the whole front end, one file (map: Leaflet + OpenStreetMap tiles)
site/data/listings.json         generated; committed only when listings change
```

`git log site/data/listings.json` is a history of listings appearing and closing.

## One-time setup

1. **Pages:** repo Settings -> Pages -> Source: **GitHub Actions**.
2. **RescueGroups key (optional):** request a free public API key at
   https://rescuegroups.org/services/adoptable-pet-data-api/ and save it under
   Settings -> Secrets and variables -> Actions as `RESCUEGROUPS_API_KEY`.
   Until then that source is skipped and the page says so.
3. Run the workflow once from the Actions tab, or wait for the daily run.

## Run it locally

```
python -m unittest discover tests
python -m refresh
python -m http.server -d site 8000     # then open http://localhost:8000
```

## Maintaining it

- **A program changed** (hours, address, paused): edit `data/programs.json` and
  update its `checked` date.
- **A breed or temperament word is not recognized:** add a line to the tables at
  the top of `refresh/tagging.py`.
- **PAWS NY listings drop to zero:** the listing site changed its HTML. The job
  keeps the last good listings and the page shows a warning. Fix `parse_index`
  or `parse_listing` in `refresh/sources/paws_ny.py`; the fixtures in
  `tests/fixtures` show the HTML they were written against.
- **Add a source:** write a module with `SOURCE_ID`, `LABEL` and `fetch(config)`
  and add it to `refresh/sources/__init__.py`. Idealist's Listings API would be
  the natural next one; access is by inquiry at https://www.idealist.org/en/open-network-api.
- **Change the default location or radius:** `data/config.json`.

## Notes

- The PAWS NY source makes about 20 requests per run, one per second, to pages
  that the site's robots.txt allows. Please keep it at one run a day.
- The RescueGroups adapter follows the published v5 documentation but has not
  run against the live API yet, because that needs a key.
- Size is the typical size for the breed when a listing gives no weight.
  Temperament is the poster's own wording. Meet the pet before you commit.
- GitHub pauses scheduled workflows after 60 days without repository activity;
  it emails you first, and one click re-enables them.
