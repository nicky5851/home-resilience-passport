"""N9: the assessment pipeline, offline (recorded responses, mocked network)."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.adapters import flood
from app.adapters.cache import DbCache
from app.adapters.climate import CLIMATE_URL
from app.db.load_rofrs import load
from app.db.session import make_sessionmaker
from app.schemas import Address, Passport, PropertyFacts
from app.schemas.api import Assessment
from app.services import assessment
from tests.conftest import DEMO_SLUGS, RECORDED_DIR, load_fixture, log_in

API = "/api/v1"
pytestmark = pytest.mark.anyio
WESTMINSTER = {
    "uprn": None,
    "line1": "1 Test Street",
    "postcode": "SW1A 1AA",
    "lat": 51.501009,
    "lon": -0.141588,
    "local_authority": "Westminster",
    "country": "england",
}
FLAT = {"property_type": "flat", "floor_level": 2, "top_floor": True, "source": "user"}


def _open_meteo(request: httpx.Request) -> httpx.Response:
    start = request.url.params["start_date"][:4]
    name = "london_1991_2020" if start == "1991" else "london_2041_2050"
    return httpx.Response(
        200, json=json.loads((RECORDED_DIR / "climate" / f"{name}.json").read_text())
    )


@pytest.fixture
def online(mock_http):
    """Open-Meteo answers with the London recordings; the EA feed with York (no warnings)."""
    climate = mock_http.get(url__startswith=CLIMATE_URL).mock(side_effect=_open_meteo)
    floods = json.loads((RECORDED_DIR / "flood" / "floods_york.json").read_text())
    warnings = mock_http.get(url__startswith=flood.FLOOD_WARNINGS_URL).mock(
        return_value=httpx.Response(200, json=floods)
    )
    return climate, warnings


def _create(client, address: dict, prop: dict | None = FLAT):
    household = load_fixture("city-top-flat")["household"]
    body = {"address": address, "household": household, "property_override": prop}
    return client.post(f"{API}/homes", json=body)


# --- API --------------------------------------------------------------------------------------


def test_real_postcode_end_to_end(user_client, online) -> None:
    res = _create(user_client, WESTMINSTER)
    assert res.status_code == 201, res.text
    home_id = res.json()["home_id"]

    res = user_client.post(f"{API}/homes/{home_id}/assess")
    assert res.status_code == 200, res.text
    a = Assessment.model_validate(res.json())
    assert (a.inputs.hot_days_baseline, a.inputs.hot_days_2050) == (2.6, 8.6)  # real, not defaults
    assert a.inputs.rofrs_band is None  # flood_postcodes is empty in tests: unknown, never "none"
    # No certificate band: our model fills it in (N13); the user's own facts are kept.
    estimated = a.inputs.property
    assert estimated.source == "model" and estimated.epc_rating is not None
    assert estimated.model_dump(include=set(FLAT) - {"source"}) == {
        k: v for k, v in FLAT.items() if k != "source"
    }
    assert [lvl.hazard for lvl in a.risk.levels][:3] == ["river_sea_flood", "overheating", "storm"]

    assert abs(a.risk.generated_at - datetime.now(UTC)) < timedelta(minutes=1)  # not L's fixed time
    assert user_client.get(f"{API}/homes/{home_id}/risk").json() == res.json()
    p = Passport.model_validate(user_client.get(f"{API}/homes/{home_id}/passport").json())
    assert p.latest_score == a.score
    assert p.address.postcode == "SW1A 1AA" and p.property.source == "user"
    assert [e.kind for e in p.events][-1] == "assessed"
    assert p.events[-1].score_after == a.score.value


def test_homes_and_assessments_are_stored(user_client, online, db_url) -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    home_id = _create(user_client, WESTMINSTER).json()["home_id"]
    user_client.post(f"{API}/homes/{home_id}/assess")

    async def counts() -> list[int]:
        eng = create_async_engine(db_url, poolclass=NullPool)
        async with eng.connect() as conn:
            out = [
                (await conn.execute(text(f"SELECT count(*) FROM {t} WHERE {col} = :id"),
                                    {"id": home_id})).scalar_one()
                for t, col in (("homes", "id"), ("households", "home_id"),
                               ("assessments", "home_id"), ("passport_events", "home_id"))
            ]  # fmt: skip
        await eng.dispose()
        return out

    import asyncio

    assert asyncio.run(counts()) == [1, 1, 1, 1]
    assert [h["home_id"] for h in user_client.get(f"{API}/homes").json()] == [home_id]


def test_second_assessment_is_served_from_the_cache(user_client, online) -> None:
    climate, warnings = online
    home_id = _create(user_client, WESTMINSTER).json()["home_id"]
    user_client.post(f"{API}/homes/{home_id}/assess")
    user_client.post(f"{API}/homes/{home_id}/assess")
    assert (climate.call_count, warnings.call_count) == (2, 1)


def test_slow_warnings_feed_counts_zero(user_client, online, monkeypatch) -> None:
    import asyncio

    from app.services import assessment as svc

    async def slow(*args) -> int:
        await asyncio.sleep(1)
        return 7

    monkeypatch.setattr(svc, "ASSESS_WARNINGS_BUDGET_S", 0.05)
    monkeypatch.setattr(svc.flood, "active_flood_warnings", slow)
    home_id = _create(user_client, WESTMINSTER).json()["home_id"]
    a = Assessment.model_validate(user_client.post(f"{API}/homes/{home_id}/assess").json())
    assert a.inputs.active_flood_warnings == 0


def test_network_off_still_assesses(user_client) -> None:
    """`client` has Open-Meteo and the EA feed offline: regional defaults and 0 warnings."""
    home_id = _create(user_client, WESTMINSTER).json()["home_id"]
    a = Assessment.model_validate(user_client.post(f"{API}/homes/{home_id}/assess").json())
    assert a.inputs.hot_days_2050 is not None and a.inputs.active_flood_warnings == 0


@pytest.mark.parametrize("slug", DEMO_SLUGS)
def test_demo_homes_work_offline(user_client, slug) -> None:
    f = load_fixture(slug)
    res = user_client.post(f"{API}/homes/{f['passport']['home_id']}/assess")
    assert res.status_code == 200
    assert res.json()["score"] == f["score"]  # fixtures, no network
    home_id = _create(user_client, f["address"], prop=None).json()["home_id"]  # demo property
    assert user_client.post(f"{API}/homes/{home_id}/assess").status_code == 200


def test_no_certificate_and_no_details_asks_for_them(user_client) -> None:
    res = _create(user_client, WESTMINSTER | {"uprn": "100023336956"}, prop=None)
    assert res.status_code == 400
    assert res.json()["code"] == "validation"
    assert res.json()["detail"].startswith("property_override:")


def test_other_users_cannot_assess(client) -> None:
    log_in(client, "owner@example.com")
    home_id = _create(client, WESTMINSTER).json()["home_id"]
    log_in(client, "other@example.com")
    assert client.post(f"{API}/homes/{home_id}/assess").status_code == 404
    assert client.post(f"{API}/homes/{uuid.uuid4()}/assess").status_code == 404


# --- Service with Postgres (flood band and cache share one session) --------------------------


async def test_pipeline_with_the_database(engine, online, postcodes_io) -> None:
    await load(engine, {"SW1A 1AA": "medium"})
    try:
        address = Address.model_validate(WESTMINSTER)
        prop = PropertyFacts.model_validate(FLAT)
        async with make_sessionmaker(engine)() as s:
            first = await assessment.hazard_inputs(address, prop, s, DbCache(s))
        async with make_sessionmaker(engine)() as s:
            second = await assessment.hazard_inputs(address, prop, s, DbCache(s))
        assert first == second
        assert first.rofrs_band == "medium"
        assert first.hot_days_2050 == 8.6
        assert online[0].call_count == 2  # second run from api_cache
    finally:
        await load(engine, {})
