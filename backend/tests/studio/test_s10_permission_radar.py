"""S10: the rule table (listed -> consent, conservation+wall insulation -> check council,
flat+external -> check council, API down -> all null + safe defaults), and every plan measure
gets a verdict."""

import httpx
import pytest

from app.schemas.plan import Measure
from app.schemas.property import PropertyFacts
from app.studio.features.s10_permission_radar.config import PLANNING_DATA_BASE
from app.studio.features.s10_permission_radar.service import family_for, verdict_for

API = "/api/v1"


def _measure(id: str, name: str) -> Measure:
    return Measure(
        id=id,
        name=name,
        category="storm",
        cost_low_gbp=0,
        cost_high_gbp=0,
        annual_bill_saving_gbp=0,
        co2_saved_kg_per_year=0,
        resilience_points=0,
        renter_ok=True,
        needs_landlord=False,
        source_url="https://example.com",
    )


def _house(**kwargs) -> PropertyFacts:
    defaults = dict(property_type="semi_detached", source="demo")
    defaults.update(kwargs)
    return PropertyFacts(**defaults)


def test_family_for_keywords() -> None:
    assert family_for("external-shutters", "External window shutters") == "windows"
    assert family_for("roof-fixings", "Roof and ridge tile fixings") == "roofing"
    assert family_for("flood-door", "Flood door") == "doors"
    assert family_for("led-lighting", "LED lighting") == "other"


def test_listed_building_needs_consent() -> None:
    measure = _measure("ext-wall", "External wall cladding")
    verdict = verdict_for(measure, "wall_insulation", _house(), {"listed-building-outline": True})
    assert verdict.verdict == "consent_needed"


def test_conservation_area_wall_insulation_checks_council() -> None:
    measure = _measure("ext-wall", "External wall cladding")
    verdict = verdict_for(
        measure,
        "wall_insulation",
        _house(),
        {"listed-building-outline": False, "conservation-area": True},
    )
    assert verdict.verdict == "check_council"


def test_flat_external_checks_council() -> None:
    measure = _measure("roof-fixings", "Roof and ridge tile fixings")
    verdict = verdict_for(measure, "roofing", _house(property_type="flat"), {})
    assert verdict.verdict == "check_council"


def test_flat_internal_likely_permitted() -> None:
    measure = _measure("led-lighting", "LED lighting")
    verdict = verdict_for(measure, "other", _house(property_type="flat"), {})
    assert verdict.verdict == "likely_permitted"


def test_api_down_defaults_external_to_check_council() -> None:
    measure = _measure("roof-fixings", "Roof and ridge tile fixings")
    verdict = verdict_for(
        measure,
        "roofing",
        _house(),
        {"conservation-area": None, "listed-building-outline": None},
    )
    assert verdict.verdict == "check_council"


def test_otherwise_likely_permitted() -> None:
    measure = _measure("flood-plan-kit", "Flood plan and grab bag")
    verdict = verdict_for(measure, "other", _house(), {"conservation-area": False})
    assert verdict.verdict == "likely_permitted"


@pytest.fixture
def planning_data_api(mock_http):
    return mock_http.get(url__startswith=PLANNING_DATA_BASE).mock(
        return_value=httpx.Response(200, json={"entities": [], "count": 0, "links": {}})
    )


def test_route_gives_every_measure_a_verdict(client, planning_data_api) -> None:
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/permission-radar")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["measures"]) >= 1
    assert all(
        m["verdict"] in ("likely_permitted", "check_council", "consent_needed", "not_applicable")
        for m in body["measures"]
    )
    assert len(body["constraints"]) == 7


def test_route_falls_back_offline(client, mock_http) -> None:
    mock_http.get(url__startswith=PLANNING_DATA_BASE).mock(
        side_effect=httpx.ConnectError("offline")
    )
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/permission-radar")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["fallback_used"] is True
    assert all(c["applies"] is None for c in body["constraints"])
