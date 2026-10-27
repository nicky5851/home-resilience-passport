"""Load A's reference CSVs into the database (`make seed`).

uv run python -m app.db.seed

Refuses to load anything if `make validate-data` would fail. The measures and funding tables
are replaced as a whole so they always mirror the CSVs. Demo homes are served from the
fixtures until N15 seeds them with full data.
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine

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


async def _main() -> int:
    engine = get_engine()
    try:
        counts = await seed(engine)
    except SeedError as e:
        print(f"Seed refused, fix the CSVs first:\n{e}")
        return 1
    finally:
        await engine.dispose()
    print("Seeded " + ", ".join(f"{n} {table}" for table, n in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
