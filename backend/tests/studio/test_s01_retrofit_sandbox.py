"""S01: hotspot mapping over the real CSV, sandbox init/simulate against demo + real homes."""

import uuid

import pytest

from app.studio.features.s01_retrofit_sandbox.config import HOTSPOT_LABELS, hotspot_for
from tests.conftest import DEMO_SLUGS

API = "/api/v1"
pytestmark = pytest.mark.anyio


async def _measures(engine):
    from app.db.session import make_sessionmaker
    from app.services import planner

    async with make_sessionmaker(engine)() as session:
        return await planner.load_measures(session)


async def test_every_real_measure_maps_to_exactly_one_hotspot(engine) -> None:
    measures = await _measures(engine)
    assert measures, "seed data must be loaded (`make seed`)"
    for m in measures:
        hotspot = hotspot_for(m.id, m.name)
        assert hotspot in HOTSPOT_LABELS


def test_hotspot_rules_cover_the_named_families() -> None:
    assert hotspot_for("loft-insulation", "Loft insulation top-up") == "roof"
    assert hotspot_for("flood-door", "Flood door") == "door"
    assert hotspot_for("external-shutters", "External window shutters") == "windows"
    assert hotspot_for("drain-survey", "Drain survey and repair") == "ground"
    assert hotspot_for("led-lighting", "LED lighting throughout") == "services"


def test_sandbox_init_works_logged_out_on_a_demo_home(client) -> None:
    res = client.get(f"{API}/studio/homes/demo-{DEMO_SLUGS[0]}/sandbox")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["hotspots"]
    assert body["measures"]
    assert body["baseline"]["score"]["value"] is not None


def test_sandbox_simulate_matches_a_direct_compute_score_call(client) -> None:
    init = client.get(f"{API}/studio/homes/demo-{DEMO_SLUGS[0]}/sandbox").json()
    measure_id = init["measures"][0]["measure"]["id"]

    res = client.post(
        f"{API}/studio/homes/demo-{DEMO_SLUGS[0]}/sandbox/simulate",
        json={"measure_ids": [measure_id]},
    )
    assert res.status_code == 200, res.text
    state = res.json()
    assert state["score"]["value"] >= init["baseline"]["score"]["value"]
    assert state["cost_low_gbp"] >= 0


def test_simulate_rejects_a_measure_not_in_this_home(client) -> None:
    res = client.post(
        f"{API}/studio/homes/demo-{DEMO_SLUGS[0]}/sandbox/simulate",
        json={"measure_ids": ["not-a-real-measure"]},
    )
    assert res.status_code == 400, res.text
    assert res.json()["code"] == "validation"


def test_simulate_rejects_more_than_thirty_ids(client) -> None:
    res = client.post(
        f"{API}/studio/homes/demo-{DEMO_SLUGS[0]}/sandbox/simulate",
        json={"measure_ids": [f"id-{i}" for i in range(31)]},
    )
    assert res.status_code == 400, res.text


def test_other_users_home_is_404(client, user_client) -> None:
    from tests.conftest import load_fixture, log_in
    from tests.studio.test_hub import FLAT, WESTMINSTER

    household = load_fixture("city-top-flat")["household"]
    body = {"address": WESTMINSTER, "household": household, "property_override": FLAT}
    home_id = user_client.post(f"{API}/homes", json=body).json()["home_id"]
    user_client.post(f"{API}/homes/{home_id}/assess")

    log_in(client, "someone-else-s01@example.com")
    res = client.get(f"{API}/studio/homes/{home_id}/sandbox")
    assert res.status_code == 404, res.text


def test_unknown_uuid_ref_without_login_is_401(client) -> None:
    res = client.get(f"{API}/studio/homes/{uuid.uuid4()}/sandbox")
    assert res.status_code == 401, res.text
