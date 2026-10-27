"""Demo-home fixtures from the real pipeline (spec §4.4, N8 hand-off).

uv run python -m scripts.make_fixtures            # `make fixtures`: outputs only, offline
uv run python -m scripts.make_fixtures --inputs   # `make fixtures-inputs`: record real inputs first

Outputs (`risk`, `score`, and the passport's `latest_risk` / `latest_score`) are recomputed from
each fixture's inputs with L's scoring (`app.scoring`), so they always match the inputs. Either
coder may refresh them (spec §3.3). `plan` and `funding` stay as they are until N11 / L6 build them.

`--inputs` changes contract data (spec §3.3: the PR needs L's approval). It records:
- `rofrs_band` from `flood_postcodes` (run `make flood-data` first; refuses an unknown band),
- the six climate fields from Open-Meteo (real answers only: retries through the per-minute
  limit and refuses the regional defaults).
It keeps `property` and `subsidence_signal` (the demo's household facts and answers) and
`active_flood_warnings` (a live value: a snapshot would change from hour to hour).
"""

import asyncio
import json
import sys
from pathlib import Path

from app.adapters import climate, flood, postcodes
from app.adapters.cache import DbCache
from app.db.session import get_engine, make_sessionmaker
from app.schemas import HazardInputs, PropertyFacts
from app.scoring import assess_risk, compute_score

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "demo_homes"
CLIMATE_FIELDS = (
    "hot_days_baseline",
    "hot_days_2050",
    "heavy_rain_days_baseline",
    "heavy_rain_days_2050",
    "max_wind_baseline_kmh",
    "max_wind_2050_kmh",
)
RETRIES = 6
RETRY_WAIT_S = 65  # Open-Meteo's free tier has a per-minute limit


class FixtureError(RuntimeError):
    pass


def refresh_outputs(fixture: dict) -> dict:
    """Recompute risk and score from the fixture's inputs (pure, offline)."""
    inputs = HazardInputs.model_validate(fixture["inputs"])
    risk = assess_risk(inputs)
    score = compute_score(risk, PropertyFacts.model_validate(fixture["property"]))
    fixture["risk"] = risk.model_dump(mode="json")
    fixture["score"] = score.model_dump(mode="json")
    fixture["passport"]["latest_risk"] = fixture["risk"]
    fixture["passport"]["latest_score"] = fixture["score"]
    return fixture


async def record_inputs(fixture: dict, cache: DbCache, session) -> dict:
    a = fixture["address"]
    band = await flood.rofrs_band(a["postcode"], a["country"], session)
    if band is None and a["country"] == "england":
        raise FixtureError(f"{fixture['slug']}: flood band unknown; run `make flood-data` first")
    info = await postcodes.lookup_postcode(a["postcode"], cache)
    for attempt in range(RETRIES):
        stats = await climate.climate_stats(a["lat"], a["lon"], cache, region=info.region)
        if not stats.from_defaults:
            break
        if attempt == RETRIES - 1:
            raise FixtureError(f"{fixture['slug']}: Open-Meteo did not answer; try again later")
        print(f"  Open-Meteo busy, waiting {RETRY_WAIT_S} s ...", flush=True)
        await asyncio.sleep(RETRY_WAIT_S)
    inputs = fixture["inputs"]
    inputs["rofrs_band"] = band
    for field in CLIMATE_FIELDS:
        inputs[field] = getattr(stats, field)
    HazardInputs.model_validate(inputs)
    return fixture


def _write(path: Path, fixture: dict) -> None:
    path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")


async def _record_all(paths: list[Path]) -> None:
    engine = get_engine()
    try:
        async with make_sessionmaker(engine)() as session:
            cache = DbCache(session)
            for path in paths:
                fixture = await record_inputs(json.loads(path.read_text()), cache, session)
                _write(path, fixture)
                i = fixture["inputs"]
                print(
                    f"{fixture['slug']:17} band={i['rofrs_band']} "
                    + " ".join(f"{f}={i[f]}" for f in CLIMATE_FIELDS),
                    flush=True,
                )
    finally:
        await engine.dispose()


def main(argv: list[str]) -> int:
    paths = sorted(FIXTURES_DIR.glob("*.json"))
    if "--inputs" in argv:
        try:
            asyncio.run(_record_all(paths))
        except FixtureError as e:
            print(f"make fixtures refused: {e}")
            return 1
    for path in paths:
        fixture = refresh_outputs(json.loads(path.read_text()))
        _write(path, fixture)
        print(f"{fixture['slug']:17} risk + score refreshed (score {fixture['score']['value']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
