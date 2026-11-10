"""Small, polite HTTP helper: one request per second, clear User-Agent, a couple of retries."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

USER_AGENT = "borrowed-paws/1.0 (personal volunteer-listing finder; +https://github.com/jjjjgyj/free-paws)"
MIN_GAP_SECONDS = 1.0
_last_request = 0.0


def fetch(url: str, *, data: dict | None = None, headers: dict | None = None,
          timeout: int = 30, retries: int = 2) -> str:
    """GET (or POST when `data` is given) and return the body as text."""
    global _last_request
    body = json.dumps(data).encode() if data is not None else None
    req_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        wait = MIN_GAP_SECONDS - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        try:
            req = urllib.request.Request(url, data=body, headers=req_headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as err:
            if err.code < 500 and err.code != 429:
                raise  # a 4xx will not get better by retrying
            last_error = err
        except (urllib.error.URLError, TimeoutError) as err:
            last_error = err
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"giving up on {url}: {last_error}")


def fetch_json(url: str, **kwargs) -> dict:
    return json.loads(fetch(url, **kwargs))
