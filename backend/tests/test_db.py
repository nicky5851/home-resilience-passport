"""N4: migrations, seed and cascading deletes against a real Postgres."""

import uuid

import pytest
from sqlalchemy import func, inspect, select

from alembic import command
from app.db.models import (
    Assessment,
    Base,
    FundingOption,
    Home,
    Household,
    Measure,
    PassportEvent,
    SavedPlan,
    ShareLink,
    User,
    WorkFile,
)
from app.db.reference import load_reference
from app.db.seed import SeedError, seed
from app.db.session import make_sessionmaker
from tests.conftest import alembic_config

pytestmark = pytest.mark.anyio

SPEC_TABLES = {
    "users", "homes", "households", "assessments", "plans", "passport_events", "work_files",
    "share_links", "measures", "funding_options", "flood_postcodes", "api_cache", "llm_cache",
}  # fmt: skip
HOME_TABLES = (Household, Assessment, SavedPlan, PassportEvent, WorkFile, ShareLink)


async def _tables(engine) -> set[str]:
    async with engine.connect() as conn:
        return set(await conn.run_sync(lambda c: inspect(c).get_table_names()))


async def test_fresh_database_has_every_table(engine) -> None:
    assert SPEC_TABLES <= await _tables(engine)
    assert set(Base.metadata.tables) == SPEC_TABLES


def test_downgrade_and_upgrade_again(db_url: str) -> None:
    cfg = alembic_config(db_url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


async def test_seed_loads_and_reads_a_measure_back(engine) -> None:
    counts = await seed(engine)
    ref = load_reference()
    assert counts == {
        "measures": len(ref.rows["measures.csv"]),
        "funding_options": len(ref.rows["funding.csv"]),
    }
    async with make_sessionmaker(engine)() as s:
        m = await s.get(Measure, "flood-door")
        assert m is not None and m.category == "flood" and m.cost_low_gbp <= m.cost_high_gbp
        assert m.hazards_reduced == ["river_sea_flood", "surface_water"]
        assert await s.scalar(select(func.count()).select_from(FundingOption)) == len(
            ref.rows["funding.csv"]
        )
    assert await seed(engine) == counts  # running twice replaces, never duplicates


async def test_seed_refuses_invalid_csvs(engine, tmp_path) -> None:
    for name in ("demo_homes.csv", "measures.csv", "funding.csv"):
        (tmp_path / name).write_text("wrong,header\n")
    with pytest.raises(SeedError, match="header must be exactly"):
        await seed(engine, tmp_path)


async def test_deleting_a_user_removes_everything(engine) -> None:
    sm = make_sessionmaker(engine)
    user_id, home_id, event_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with sm() as s, s.begin():
        s.add(User(id=user_id, email=f"{user_id}@example.com", hashed_password="x"))
        await s.flush()
        s.add(
            Home(id=home_id, user_id=user_id, line1="1 Test St", postcode="YO1 9TJ", lat=0,
                 lon=0, country="england", property={"property_type": "flat"})
        )  # fmt: skip
        await s.flush()
        s.add_all([
            Household(home_id=home_id, tenure="owner_occupier", income_band="under_20k",
                      budget_gbp=0, priorities=["comfort"], vulnerable=None),
            Assessment(home_id=home_id, inputs={}, risk={}, score={}, scoring_version="v1"),
            SavedPlan(home_id=home_id, budget_gbp=0, selected_ids=[], plan={}),
            PassportEvent(id=event_id, home_id=home_id, kind="work_recorded", detail={}),
            ShareLink(home_id=home_id, token=uuid.uuid4().hex),
        ])  # fmt: skip
        await s.flush()
        s.add(
            WorkFile(event_id=event_id, storage_key=f"{uuid.uuid4()}.pdf",
                     certificate_name="c.pdf", content_type="application/pdf", size_bytes=4)
        )  # fmt: skip

    async def count(model, col, value) -> int:
        async with sm() as s:
            return await s.scalar(select(func.count()).select_from(model).where(col == value))

    assert await count(Home, Home.user_id, user_id) == 1
    for model in HOME_TABLES:
        col = WorkFile.event_id if model is WorkFile else model.home_id
        assert await count(model, col, event_id if model is WorkFile else home_id) == 1

    async with sm() as s, s.begin():
        await s.delete(await s.get(User, user_id))

    assert await count(Home, Home.user_id, user_id) == 0
    for model in HOME_TABLES:
        col = WorkFile.event_id if model is WorkFile else model.home_id
        assert await count(model, col, event_id if model is WorkFile else home_id) == 0, model
