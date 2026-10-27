"""N6: EPC register adapter, offline.

recorded/epc/ holds responses recorded from the register's integration API on 2026-10-27
(its test data: SW1A 1AA and CF10 1EP). Integration has no flats, so
`certificate_0001-0001-0001-0001-0001.json` is the register's official RdSAP-17.0 flat sample
(github.com/communitiesuk/epb-data-warehouse, spec/fixtures/json_samples) in the API's
`{"data": ...}` wrapper.
"""

import json

import httpx
import pytest

from app.adapters import epc
from app.adapters.http import UpstreamUnavailable
from app.config import get_settings
from app.schemas.api import PostcodeLookup
from tests.conftest import RECORDED_DIR, load_fixture

API = "/api/v1"
EPC_DIR = RECORDED_DIR / "epc"
NOT_FOUND = {"data": {"error": "No certificates could be found for that query"}}  # as recorded
pytestmark = pytest.mark.anyio


def _recorded(request: httpx.Request) -> httpx.Response:
    """Postcode search → its recording; UPRN search → matching rows; certificate → its file."""
    q = request.url.params
    if request.url.path == "/api/certificate":
        path = EPC_DIR / f"certificate_{q['certificate_number']}.json"
    elif "postcode" in q:
        path = EPC_DIR / f"search_{q['postcode'].replace(' ', '')}.json"
    else:
        rows = [
            r
            for f in EPC_DIR.glob("search_*.json")
            for r in json.loads(f.read_text())["data"]
            if r["uprn"] is not None and str(r["uprn"]).zfill(12) == q["uprn"]
        ]
        if not rows:
            return httpx.Response(404, json=NOT_FOUND)
        return httpx.Response(200, json={"data": rows})
    if not path.exists():
        return httpx.Response(404, json=NOT_FOUND)
    return httpx.Response(200, json=json.loads(path.read_text()))


@pytest.fixture
def recorded_epc(epc_api):
    epc_api.side_effect = _recorded
    return epc_api


def _certificate(number: str) -> dict:
    return json.loads((EPC_DIR / f"certificate_{number}.json").read_text())["data"]


# --- Search ---------------------------------------------------------------------------------


async def test_search_lists_latest_certificate_per_address(recorded_epc, memory_cache) -> None:
    found = await epc.search_postcode("SW1A 1AA", memory_cache)
    assert [(a.line1, a.uprn, a.epc_rating) for a in found] == [
        ("102 Buckingham Palace", None, "E"),
        ("123 Main Street, Apartment 4B", "10033527301", "D"),
        ("Buckingham Palace, The Mall", "10033544614", "D"),  # two certificates, one address
    ]


async def test_same_day_certificates_pick_the_same_one_in_any_order(
    recorded_epc, memory_cache
) -> None:
    rows = json.loads((EPC_DIR / "search_SW1A1AA.json").read_text())["data"]
    forward = epc.latest_per_address(rows)
    backward = epc.latest_per_address(list(reversed(rows)))
    assert forward == backward
    palace = next(a for a in forward if a.uprn == "10033544614")
    assert palace.certificate_number == "2106-5106-4957-3526-5651"


async def test_search_wales(recorded_epc, memory_cache) -> None:
    found = await epc.search_postcode("CF10 1EP", memory_cache)
    assert [(a.line1, a.epc_rating) for a in found] == [
        ("1 Some Street, Some Area, Some County", "C"),
        ("1 Some Street, Some Area, Some County", "C"),  # two UPRNs, same address text
    ]


async def test_search_nothing_registered_is_empty(recorded_epc, memory_cache) -> None:
    assert await epc.search_postcode("E1 8NG", memory_cache) == []


async def test_search_sends_bearer_token(recorded_epc, memory_cache) -> None:
    await epc.search_postcode("SW1A 1AA", memory_cache)
    request = recorded_epc.calls.last.request
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.headers["Accept"] == "application/json"
    assert request.url.params["postcode"] == "SW1A 1AA"


async def test_base_url_comes_from_settings(epc_api, mock_http, memory_cache, monkeypatch) -> None:
    integration = "https://api.get-energy-performance-data.epb-integration.communities.gov.uk"
    monkeypatch.setattr(get_settings(), "epc_api_base_url", integration + "/")
    route = mock_http.get(url__startswith=integration).mock(
        return_value=httpx.Response(404, json=NOT_FOUND)
    )
    await epc.search_postcode("SW1A 1AA", memory_cache)
    assert route.call_count == 1 and epc_api.call_count == 0
    assert str(route.calls.last.request.url).startswith(integration + "/api/domestic/search?")


async def test_search_is_cached(recorded_epc, memory_cache) -> None:
    await epc.search_postcode("SW1A 1AA", memory_cache)
    await epc.search_postcode("SW1A 1AA", memory_cache)
    assert recorded_epc.call_count == 1


async def test_missing_token_degrades(epc_api, memory_cache, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "epc_api_token", None)
    with pytest.raises(UpstreamUnavailable):
        await epc.search_postcode("SW1A 1AA", memory_cache)
    assert epc_api.call_count == 0


@pytest.mark.parametrize(
    "failure",
    [
        httpx.ConnectTimeout("timed out"),
        # Recorded: a token for the wrong environment gets 403 UNAUTHORISED.
        httpx.Response(
            403, json={"errors": [{"code": "UNAUTHORISED", "title": "You are not authenticated"}]}
        ),
        httpx.Response(500),
    ],
)
async def test_register_failure(epc_api, memory_cache, failure) -> None:
    if isinstance(failure, Exception):
        epc_api.side_effect = failure
    else:
        epc_api.return_value = failure
    with pytest.raises(UpstreamUnavailable):
        await epc.search_postcode("SW1A 1AA", memory_cache)
    assert memory_cache.rows == {}


# --- Certificate → PropertyFacts --------------------------------------------------------------


def test_map_house() -> None:
    facts = epc.map_certificate(_certificate("0502-9668-3722-8429-1243"))
    assert facts.model_dump() == {
        "property_type": "detached",
        "built_form": "Detached",
        "construction_age_band": "before 1900",
        "floor_area_m2": 64.0,
        "floor_level": 0,
        "top_floor": None,
        "main_heating": "Boiler and radiators, mains gas",
        "main_fuel": "mains gas",
        "epc_rating": "D",
        "epc_score": 60,
        "co2_tonnes_per_year": 2.2,
        "source": "epc_api",
    }


def test_map_house_with_wrapped_text() -> None:
    """RdSAP-20 certificates wrap descriptions as {"value": ..., "language": ...}."""
    facts = epc.map_certificate(_certificate("2106-5106-4957-3526-5651"))
    assert facts.main_heating == "Boiler and radiators, mains gas"
    assert (facts.property_type, facts.floor_area_m2) == ("detached", 1007.0)


def test_map_electric_house() -> None:
    facts = epc.map_certificate(_certificate("2230-0021-2000-0036-0202"))
    assert (facts.main_heating, facts.main_fuel) == ("Room heaters, electric", "electricity")
    assert (facts.construction_age_band, facts.epc_rating, facts.epc_score) == (
        "1983-1990",
        "E",
        44,
    )


def test_map_new_build_sap_house() -> None:
    facts = epc.map_certificate(_certificate("0000-0000-9876-5432-1003"))
    assert (facts.property_type, facts.built_form) == ("terraced", "Mid-Terrace")
    assert (facts.epc_rating, facts.epc_score, facts.floor_area_m2) == ("C", 72, 165.0)


def test_fuel_follows_the_heating_description() -> None:
    """This certificate codes bottled LPG but describes electric heating; the user sees the
    description, so the fuel must match it."""
    cert = _certificate("0000-0000-9876-5432-1003")
    assert cert["sap_heating"]["main_heating_details"][0]["main_fuel_type"] == 5  # LPG in SAP-19.2
    facts = epc.map_certificate(cert)
    assert (facts.main_heating, facts.main_fuel) == (
        "Boiler and radiators, electric",
        "electricity",
    )


def test_coded_fuel_when_description_names_none() -> None:
    cert = _certificate("0502-9668-3722-8429-1243")
    cert["main_heating"] = [{"description": "Community scheme"}]
    assert epc.map_certificate(cert).main_fuel == "mains gas"  # RdSAP code 26


def test_map_flat() -> None:
    facts = epc.map_certificate(_certificate("0001-0001-0001-0001-0001"))
    assert facts.model_dump() == {
        "property_type": "flat",
        "built_form": "Semi-Detached",
        "construction_age_band": "1950-1966",
        "floor_area_m2": 55.0,
        "floor_level": 1,
        "top_floor": False,
        "main_heating": "Electric storage heaters",
        "main_fuel": "electricity",
        "epc_rating": "D",
        "epc_score": 66,
        "co2_tonnes_per_year": 3.9,
        "source": "epc_api",
    }


def test_map_top_floor_flat() -> None:
    cert = _certificate("0001-0001-0001-0001-0001")
    cert["sap_flat_details"] = {"level": 3, "top_storey": "Y", "flat_location": "05"}
    facts = epc.map_certificate(cert)
    assert (facts.floor_level, facts.top_floor) == (5, True)


def test_map_missing_fields_are_null() -> None:
    facts = epc.map_certificate({"schema_type": "RdSAP-Schema-21.0.1", "property_type": 1})
    assert facts.property_type == "bungalow"
    assert facts.epc_rating is None and facts.main_fuel is None and facts.floor_area_m2 is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("mains gas (not community)", "mains gas"),
        ("Gas: mains gas", "mains gas"),
        (
            "electricity - this is for backwards compatibility only and should not be used",
            "electricity",
        ),
        ("oil (not community)", "oil"),
        ("bottled LPG", "LPG"),
        ("smokeless coal", "coal"),
        ("wood logs", "wood"),
        ("biomass (community)", "biofuel"),
        ("B30K (not community)", None),
        (None, None),
    ],
)
def test_simplify_fuel(raw, expected) -> None:
    assert epc.simplify_fuel(raw) == expected


async def test_property_facts_for_uprn(recorded_epc, memory_cache) -> None:
    facts = await epc.property_facts_for_uprn("10033544614", memory_cache)
    assert facts is not None and facts.floor_area_m2 == 1007.0
    assert recorded_epc.calls.last.request.url.params["certificate_number"] == (
        "2106-5106-4957-3526-5651"
    )


async def test_property_facts_for_unknown_uprn_is_none(recorded_epc, memory_cache) -> None:
    assert await epc.property_facts_for_uprn("999", memory_cache) is None


# --- Route --------------------------------------------------------------------------------------


def test_route_lists_addresses_with_ratings(client, recorded_epc) -> None:
    body = PostcodeLookup.model_validate(client.get(f"{API}/lookup/postcode/SW1A1AA").json())
    assert [(a.line1, a.epc_rating) for a in body.addresses] == [
        ("102 Buckingham Palace", "E"),
        ("123 Main Street, Apartment 4B", "D"),
        ("Buckingham Palace, The Mall", "D"),
    ]


def test_route_register_down_gives_empty_list(client, epc_api) -> None:
    epc_api.side_effect = httpx.ConnectError("offline")
    res = client.get(f"{API}/lookup/postcode/SW1A1AA")
    assert res.status_code == 200
    assert res.json()["addresses"] == []


def test_route_without_token_gives_empty_list(client, epc_api, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "epc_api_token", None)
    res = client.get(f"{API}/lookup/postcode/SW1A1AA")
    assert (res.status_code, res.json()["addresses"]) == (200, [])


def test_route_demo_address_comes_first(client) -> None:
    address = load_fixture("flood-terrace")["address"]
    body = client.get(f"{API}/lookup/postcode/{address['postcode']}").json()
    assert body["addresses"][0]["line1"] == address["line1"]


# --- Settings and environments ------------------------------------------------------------------


@pytest.mark.parametrize("blank", ["", "  ", None])
def test_blank_base_url_means_live(blank) -> None:
    from app.config import EPC_API_LIVE_URL, Settings

    assert Settings(epc_api_base_url=blank).epc_api_base_url == EPC_API_LIVE_URL


async def test_cache_is_separate_per_environment(
    recorded_epc, mock_http, memory_cache, monkeypatch
) -> None:
    """Switching EPC_API_BASE_URL must not serve the other environment's cached answers."""
    await epc.search_postcode("SW1A 1AA", memory_cache)
    integration = "https://api.get-energy-performance-data.epb-integration.communities.gov.uk"
    route = mock_http.get(url__startswith=integration).mock(side_effect=_recorded)
    monkeypatch.setattr(get_settings(), "epc_api_base_url", integration)
    await epc.search_postcode("SW1A 1AA", memory_cache)
    assert route.call_count == 1  # not answered from the live entry
    assert sorted(memory_cache.rows) == [
        "epc:api.get-energy-performance-data.communities.gov.uk:search:SW1A 1AA",
        "epc:api.get-energy-performance-data.epb-integration.communities.gov.uk:search:SW1A 1AA",
    ]
