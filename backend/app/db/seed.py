"""Load A's reference CSVs into the database (`make seed`).

uv run python -m app.db.seed

Refuses to load anything if `make validate-data` would fail. The measures and funding tables
are replaced as a whole so they always mirror the CSVs.

Then the five demo homes' data goes into `api_cache` (spec N15): each one's postcode details
and climate figures, from its fixture. Looking up, adding and assessing a demo address then
needs no network and gives the fixture's numbers, so the demo runs with Wi-Fi off. (The demo
homes themselves are served from the fixtures; their flood bands come from `make flood-data`,
and live flood warnings are 0 offline.)
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters import climate, postcodes
from app.adapters.cache import Cache, DbCache
from app.api.stub_store import fixtures
from app.config import (
    CLIMATE_BASELINE_YEARS,
    CLIMATE_CACHE_TTL,
    CLIMATE_FUTURE_YEARS,
    POSTCODE_CACHE_TTL,
)
from app.db.models import FundingOption, Measure
from app.db.reference import REFERENCE_DIR, load_reference
from app.db.session import get_engine, make_sessionmaker


class SeedError(RuntimeError):
    pass


async def seed(engine: AsyncEngine, directory: Path = REFERENCE_DIR) -> dict[str, int]:
    ref = load_reference(directory)
    if ref.errors:
        raise SeedError("\n".join(str(p) for p in ref.errors))

    measures = ref.rows["measures.csv"]
    funding = ref.rows["funding.csv"]
    async with make_sessionmaker(engine)() as session, session.begin():
        await session.execute(delete(Measure))
        await session.execute(delete(FundingOption))
        session.add_all(Measure(**row) for row in measures)
        session.add_all(FundingOption(**row) for row in funding)
    return {"measures": len(measures), "funding_options": len(funding)}


async def seed_demo_cache(cache: Cache) -> int:
    """Each demo home's postcode details and climate periods, as the adapters cache them."""
    for f in fixtures().values():
        a, i = f.demo.address, f.inputs
        region = climate.default_region(a.lat, a.lon).name  # demo homes sit well inside one
        info = postcodes.PostcodeInfo(
            postcode=a.postcode,
            lat=a.lat,
            lon=a.lon,
            local_authority=a.local_authority,
            country=a.country,
            region=region,
        )
        await cache.put(
            postcodes.cache_key(a.postcode),
            postcodes.SOURCE,
            info.model_dump(mode="json"),
            POSTCODE_CACHE_TTL,
        )
        periods = {
            CLIMATE_BASELINE_YEARS: (
                i.hot_days_baseline, i.heavy_rain_days_baseline, i.max_wind_baseline_kmh
            ),
            CLIMATE_FUTURE_YEARS: (i.hot_days_2050, i.heavy_rain_days_2050, i.max_wind_2050_kmh),
        }  # fmt: skip
        for years, (hot, rain, wind) in periods.items():
            stats = climate.PeriodStats(hot_days=hot, heavy_rain_days=rain, max_wind_kmh=wind)
            key = climate.period_key(a.lat, a.lon, years)
            await cache.put(key, "open-meteo", stats.model_dump(), CLIMATE_CACHE_TTL)
    return len(fixtures())


async def _main() -> int:
    engine = get_engine()
    try:
        counts = await seed(engine)
        async with make_sessionmaker(engine)() as session:
            counts["demo_homes_cached"] = await seed_demo_cache(DbCache(session))
    except SeedError as e:
        print(f"Seed refused, fix the CSVs first:\n{e}")
        return 1
    finally:
        await engine.dispose()
    print("Seeded " + ", ".join(f"{n} {table}" for table, n in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
