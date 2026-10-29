"""S20 Lender Portfolio Lens: builds the committed sample (docs/studio/N_20_function.md §S20).

uv run python -m scripts.build_studio_portfolio   # make studio-portfolio

Samples 500 EPC certificates (seeded, deterministic) from `data/raw/epc_bulk.csv` (N12's three
regions). Keeps only non-address fields plus the outward code (postcode district); full
postcodes, UPRNs and house numbers are read only to look up the flood band and the district
centroid, then dropped. Runs L's `assess_risk`/`compute_score` on each with a neutral
household, and works out the cheapest set of carbon-category measures that would lift the
carbon score component to the EPC-C midpoint — an approximation (spec step 1): the measures
reduce future CO2 and the carbon *score*, but this sample does not attempt to recompute an
upgraded EPC band itself.

Needs Postgres running and seeded (`make seed`), for the flood band lookup. The only network
calls are to postcodes.io, once per distinct outward code, to get a real centroid for the
bubble map; the runtime route never calls out. Writes
`backend/app/studio/data/portfolio_sample.json` (committed, a few hundred KB).
"""

import asyncio
import csv
import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.adapters.climate import default_region
from app.adapters.flood import rofrs_band
from app.adapters.http import new_client
from app.config import REPO_ROOT
from app.db.session import get_engine, make_sessionmaker
from app.schemas import HazardInputs, Measure, PropertyFacts
from app.scoring import assess_risk, compute_score
from app.scoring.config import CARBON_POINTS_PER_EPC_POINT, EPC_BAND_MIDPOINT
from app.services import planner
from ml.download import OUT as RAW_PATH
from ml.features import from_bulk

SEED = 42
SAMPLE_SIZE = 500
MIN_HOMES_PER_DISTRICT = 5
OUT_PATH = REPO_ROOT / "backend" / "app" / "studio" / "data" / "portfolio_sample.json"
BANDS = ("A", "B", "C", "D", "E", "F", "G")
CARBON_C_TARGET = EPC_BAND_MIDPOINT["C"] * CARBON_POINTS_PER_EPC_POINT
OUTCODES_URL = "https://api.postcodes.io/outcodes/"


def outward_code(postcode: str) -> str:
    return postcode.strip().upper().split(" ")[0]


def read_candidates(path: Path) -> list[dict]:
    """Rows with a usable band, CO2 figure and postcode (CONTRACT §2 nulls aside)."""
    out = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            band = row["current_energy_rating"].strip().upper()
            try:
                co2 = float(row["co2_emissions_current"])
            except ValueError:
                continue
            if band in BANDS and 0 <= co2 <= 50 and outward_code(row["postcode"]):
                out.append(row)
    return out


def to_property(row: dict) -> PropertyFacts:
    feats = from_bulk(row)
    band = row["current_energy_rating"].strip().upper()
    co2 = float(row["co2_emissions_current"])
    return PropertyFacts(
        property_type=feats["property_type"],
        built_form=feats["built_form"],
        construction_age_band=feats["age_band"],
        floor_area_m2=feats["floor_area_m2"],
        main_heating=feats["heating"],
        main_fuel=feats["fuel"],
        epc_rating=band,
        epc_score=None,
        co2_tonnes_per_year=co2,
        source="epc_api",
    )


def transition_plan(
    measures: list[Measure], risk, prop: PropertyFacts
) -> tuple[int, int, int, bool]:
    """Cheapest carbon-category measures, cheapest first, until the carbon score component
    reaches the EPC-C midpoint, or the catalogue runs out (spec step 1, approximate)."""
    carbon = sorted((m for m in measures if m.category == "carbon"), key=lambda m: m.cost_low_gbp)
    applied: list[Measure] = []
    cost_low = cost_high = co2_saved = 0
    reached = compute_score(risk, prop, []).components
    carbon_points = next(c.points for c in reached if c.name == "carbon")
    for m in carbon:
        if carbon_points >= CARBON_C_TARGET:
            break
        applied.append(m)
        cost_low += m.cost_low_gbp
        cost_high += m.cost_high_gbp
        co2_saved += m.co2_saved_kg_per_year
        carbon_points = next(
            c.points for c in compute_score(risk, prop, applied).components if c.name == "carbon"
        )
    return cost_low, cost_high, co2_saved, carbon_points >= CARBON_C_TARGET


async def outcode_centroid(client: httpx.AsyncClient, outcode: str) -> tuple[float, float] | None:
    try:
        res = await client.get(OUTCODES_URL + outcode)
    except httpx.HTTPError:
        return None
    if res.status_code != 200:
        return None
    try:
        result = res.json()["result"]
        return float(result["latitude"]), float(result["longitude"])
    except (ValueError, KeyError, TypeError):
        return None


async def build() -> dict:
    rng = random.Random(SEED)
    candidates = read_candidates(RAW_PATH)
    if len(candidates) < SAMPLE_SIZE:
        raise SystemExit(f"Only {len(candidates)} usable rows in {RAW_PATH}; need {SAMPLE_SIZE}.")
    sample_rows = rng.sample(candidates, SAMPLE_SIZE)

    engine = get_engine()
    try:
        async with make_sessionmaker(engine)() as session:
            measures = await planner.load_measures(session)
            homes = []
            for row in sample_rows:
                postcode = row["postcode"].strip().upper()
                prop = to_property(row)
                band = await rofrs_band(postcode, "england", session)
                region = default_region(0.0, 0.0, from_bulk(row)["region"])
                inputs = HazardInputs(
                    rofrs_band=band,
                    active_flood_warnings=0,
                    hot_days_baseline=region.baseline.hot_days,
                    hot_days_2050=region.future.hot_days,
                    heavy_rain_days_baseline=region.baseline.heavy_rain_days,
                    heavy_rain_days_2050=region.future.heavy_rain_days,
                    max_wind_baseline_kmh=region.baseline.max_wind_kmh,
                    max_wind_2050_kmh=region.future.max_wind_kmh,
                    subsidence_signal="unknown",
                    property=prop,
                )
                risk = assess_risk(inputs)
                score = compute_score(risk, prop, [])
                cost_low, cost_high, co2_saved, reached_c = transition_plan(measures, risk, prop)
                homes.append(
                    {
                        "outcode": outward_code(postcode),
                        "property": prop.model_dump(mode="json"),
                        "risk": risk.model_dump(mode="json"),
                        "score": score.model_dump(mode="json"),
                        "transition": {
                            "cost_low_gbp": cost_low,
                            "cost_high_gbp": cost_high,
                            "co2_saved_kg_per_year": co2_saved,
                            "reached_c": reached_c,
                        },
                    }
                )
    finally:
        await engine.dispose()

    outcodes = sorted({h["outcode"] for h in homes})
    centroids: dict[str, tuple[float, float]] = {}
    async with new_client() as client:
        for code in outcodes:
            centroid = await outcode_centroid(client, code)
            if centroid is not None:
                centroids[code] = centroid

    return {
        "generated_on": datetime.now(UTC).date().isoformat(),
        "seed": SEED,
        "homes": homes,
        "district_centroids": {k: list(v) for k, v in centroids.items()},
    }


async def main() -> int:
    data = await build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, separators=(",", ":"), sort_keys=True) + "\n")
    print(f"Wrote {len(data['homes'])} homes, {len(data['district_centroids'])} districts to "
          f"{OUT_PATH.relative_to(REPO_ROOT)}")  # fmt: skip
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
