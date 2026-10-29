"""Historical climatology adapter and task library (docs/studio/N_20_function.md §S17).

- `https://archive-api.open-meteo.com/v1/archive` - **verified** 2026-10-29 by curl: a single
  request for `start_date=1991-01-01&end_date=2020-12-31` with
  `daily=temperature_2m_min,precipitation_sum,wind_gusts_10m_max` returns all 10,958 days in one
  response. Cached 365 days (`CACHE_DAYS`).
- `care_tasks.json` task guidance links: `https://www.gov.uk/prepare-for-flooding/protect-your-
  property` is **verified** live (the actual gov.uk property-protection page; the spec's named
  URL, `.../publications/prepare-your-property-for-flooding`, could not be found - this is its
  replacement). `gassaferegister.co.uk` and `energysavingtrust.org.uk` are real, well-known UK
  organisations, but their specific sub-pages returned a bot-check wall to automated fetches
  this session, so the task library links to each site's homepage rather than a guessed sub-path
  - a scope call, flagged rather than guessed.

`measures.csv` (owned by A) has no solar-PV row today, so `clean-solar-panels`'s
`measure_present: solar` condition is never true against the real reference data - the same
scope note as [[s15-measures-gap]]."""

import json
from pathlib import Path

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
ARCHIVE_SOURCE = "open_meteo_archive"
ARCHIVE_START = "1991-01-01"
ARCHIVE_END = "2020-12-31"
CACHE_DAYS = 365

CARE_TASKS_JSON = Path(__file__).resolve().parents[2] / "data" / "care_tasks.json"


def load_care_tasks() -> list[dict]:
    return json.loads(CARE_TASKS_JSON.read_text())


ICAL_TOKEN_BYTES = 24
