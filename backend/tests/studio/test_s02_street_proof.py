"""S02: peer matching, improver/upgrade inference on hand-written certificates, and the route
assembled end to end against a tiny mocked postcodes.io + EPC register."""

import asyncio
from datetime import date

import pytest

from app.schemas import PropertyFacts
from app.studio.features.s02_street_proof import service
from app.studio.features.s02_street_proof.cert import Cert, cert_from_raw, lighting_percent
from app.studio.features.s02_street_proof.config import fuel_family
from app.studio.features.s02_street_proof.service import (
    build_street_proof,
    detect_upgrades,
    is_improver,
    is_peer,
)

pytestmark = pytest.mark.anyio
API = "/api/v1"


def _cert(**over) -> Cert:
    base = dict(
        certificate_number="c1",
        uprn="1",
        address_key="uprn:1",
        registered=date(2020, 1, 1),
        sap=60,
        band="D",
        property_type="terraced",
        built_form="Mid-Terrace",
        age_band="1900-1929",
        fuel_family="gas",
        wall_desc="",
        roof_desc="",
        window_desc="",
        heating_desc="",
        lighting_desc="",
        other_text="",
    )
    base.update(over)
    return Cert(**base)


HOME = PropertyFacts(
    property_type="terraced",
    built_form="Mid-Terrace",
    construction_age_band="1900-1929",
    floor_area_m2=80,
    floor_level=0,
    top_floor=None,
    main_heating="Boiler and radiators, mains gas",
    main_fuel="mains gas",
    epc_rating="D",
    epc_score=58,
    co2_tonnes_per_year=3.0,
    source="demo",
)


def test_cert_from_raw_parses_a_summary_row_with_no_certificate_body() -> None:
    row = {
        "certificateNumber": "x1",
        "uprn": 5,
        "registrationDate": "2021-06-01",
        "currentEnergyEfficiencyBand": "D",
    }
    cert = cert_from_raw(row, None)
    assert cert is not None
    assert cert.band == "D"
    assert cert.sap is None
    assert cert.registered == date(2021, 6, 1)


def test_cert_from_raw_is_none_without_a_parsable_date() -> None:
    assert cert_from_raw({"certificateNumber": "x1"}, None) is None


def test_lighting_percent_reads_a_percentage() -> None:
    assert lighting_percent("low energy lighting in 91% of fixed outlets") == 91
    assert lighting_percent("no mention of lighting here") is None


def test_fuel_family_groups_common_fuels() -> None:
    assert fuel_family("Boiler and radiators, mains gas") == "gas"
    assert fuel_family("Electric storage heaters") == "electric"
    assert fuel_family(None) == "unknown"


def test_is_peer_matches_type_built_form_fuel_and_age_band() -> None:
    assert is_peer(_cert(), HOME) is True


def test_is_peer_rejects_a_different_property_type() -> None:
    assert is_peer(_cert(property_type="flat"), HOME) is False


def test_is_peer_allows_age_band_one_step_away() -> None:
    assert is_peer(_cert(age_band="1930-1949"), HOME) is True


def test_is_peer_rejects_age_band_two_steps_away() -> None:
    assert is_peer(_cert(age_band="1967-1975"), HOME) is False


def test_is_improver_needs_a_five_point_gain_and_two_certificates() -> None:
    assert is_improver([_cert(sap=55), _cert(sap=60)]) is True
    assert is_improver([_cert(sap=55), _cert(sap=58)]) is False
    assert is_improver([_cert(sap=55)]) is False


def test_detect_upgrades_wall_and_loft_insulation() -> None:
    earliest = _cert(
        wall_desc="cavity wall, no insulation (assumed)",
        roof_desc="pitched, no insulation (assumed)",
    )
    latest = _cert(
        wall_desc="cavity wall, as built, insulated",
        roof_desc="pitched, 270 mm loft insulation",
    )
    assert "wall_insulation" in detect_upgrades(earliest, latest)
    assert "loft_insulation" in detect_upgrades(earliest, latest)


def test_detect_upgrades_glazing_heat_pump_solar_led_boiler() -> None:
    earliest = _cert(
        window_desc="single glazed",
        heating_desc="boiler and radiators, mains gas",
        lighting_desc="low energy lighting in 10% of fixed outlets",
        other_text="",
    )
    latest = _cert(
        window_desc="double glazed",
        heating_desc="air source heat pump",
        lighting_desc="low energy lighting in 90% of fixed outlets",
        other_text="photovoltaic panels installed",
    )
    found = detect_upgrades(earliest, latest)
    assert "glazing" in found
    assert "heat_pump" in found
    assert "solar_pv" in found
    assert "led_lighting" in found


def test_detect_upgrades_boiler_upgrade_to_condensing() -> None:
    earliest = _cert(heating_desc="boiler and radiators, mains gas")
    latest = _cert(heating_desc="boiler and radiators, mains gas, condensing")
    assert "boiler_upgrade" in detect_upgrades(earliest, latest)


def test_detect_upgrades_finds_nothing_when_nothing_changed() -> None:
    c = _cert(wall_desc="cavity wall, insulated", heating_desc="boiler, condensing")
    assert detect_upgrades(c, c) == []


# --- end to end, mocked network --------------------------------------------------------------


async def test_build_street_proof_with_enough_peers_shows_stories(
    memory_cache, monkeypatch
) -> None:
    async def fake_nearest(lat, lon, radius_m, limit):
        return [f"PC{i}" for i in range(6)]

    async def fake_rows(postcode, cache):
        # one address per postcode, improver or not, all peers of HOME
        idx = int(postcode[2:])
        return [
            {
                "certificateNumber": f"{postcode}-a",
                "uprn": idx * 10 + 1,
                "registrationDate": "2019-01-01",
                "currentEnergyEfficiencyBand": "E",
            },
            {
                "certificateNumber": f"{postcode}-b",
                "uprn": idx * 10 + 1,
                "registrationDate": "2024-01-01",
                "currentEnergyEfficiencyBand": "C",
            },
        ]

    def cert_body(number: str, sap: int) -> dict:
        return {
            "certificate_number": number,
            "schema_type": "RdSAP-Schema-17.0",
            "current_energy_efficiency_band": "C" if sap > 65 else "E",
            "energy_rating_current": sap,
            "dwelling_type": "Mid-terrace house",
            "property_type": "0",
            "built_form": "4",
            "sap_building_parts": [{"construction_age_band": "B"}],
            "main_heating": [{"description": "Boiler and radiators, mains gas"}],
            "walls": [{"description": "cavity wall, no insulation (assumed)"}],
            "roofs": [{"description": "pitched, no insulation (assumed)"}],
            "windows": {"description": "single glazed"},
            "lighting": {"description": "low energy lighting in 10% of fixed outlets"},
        }

    async def fake_cert(number, cache):
        is_latest = number.endswith("-b")
        return cert_body(number, sap=75 if is_latest else 55)

    monkeypatch.setattr(service, "nearest_postcodes", fake_nearest)
    monkeypatch.setattr(service, "search_postcode_rows", fake_rows)
    monkeypatch.setattr(service, "fetch_certificate", fake_cert)

    result = await build_street_proof(HOME, 58, 51.5, -0.1, 1000, memory_cache)

    assert result.peers_count == 6
    assert result.improvers_count == 6
    assert len(result.stories) > 0
    assert result.partial is False

    body = result.model_dump_json()
    assert "uprn" not in body
    assert "addressLine" not in body


async def test_build_street_proof_hides_stories_below_k_anonymity(
    memory_cache, monkeypatch
) -> None:
    async def fake_nearest(lat, lon, radius_m, limit):
        return ["PC0"]

    async def fake_rows(postcode, cache):
        return [
            {
                "certificateNumber": "x-a",
                "uprn": 1,
                "registrationDate": "2019-01-01",
                "currentEnergyEfficiencyBand": "E",
            },
            {
                "certificateNumber": "x-b",
                "uprn": 1,
                "registrationDate": "2024-01-01",
                "currentEnergyEfficiencyBand": "C",
            },
        ]

    async def fake_cert(number, cache):
        is_latest = number.endswith("-b")
        return {
            "schema_type": "RdSAP-Schema-17.0",
            "current_energy_efficiency_band": "C" if is_latest else "E",
            "energy_rating_current": 75 if is_latest else 55,
            "dwelling_type": "Mid-terrace house",
            "property_type": "0",
            "built_form": "4",
            "sap_building_parts": [{"construction_age_band": "B"}],
            "main_heating": [{"description": "Boiler and radiators, mains gas"}],
        }

    monkeypatch.setattr(service, "nearest_postcodes", fake_nearest)
    monkeypatch.setattr(service, "search_postcode_rows", fake_rows)
    monkeypatch.setattr(service, "fetch_certificate", fake_cert)

    result = await build_street_proof(HOME, 58, 51.5, -0.1, 1000, memory_cache)

    assert result.peers_count == 1
    assert result.stories == []
    assert result.your_percentile is None


async def test_fetch_group_rows_times_out_within_its_own_budget(memory_cache, monkeypatch) -> None:
    async def slow(postcode, cache):
        await asyncio.sleep(0.05)
        return []

    monkeypatch.setattr(service, "search_postcode_rows", slow)
    rows, timed_out = await service._fetch_group_rows(["PC0"], memory_cache, 0.001)
    assert timed_out is True
    assert rows == []


def _mock_nearest_postcodes(mock_http) -> None:
    import httpx

    from app.adapters.postcodes import POSTCODES_IO_URL

    mock_http.get(url__startswith=POSTCODES_IO_URL.removesuffix("/")).mock(
        return_value=httpx.Response(200, json={"status": 200, "result": []})
    )


def test_route_rejects_radius_outside_bounds(client, mock_http) -> None:
    _mock_nearest_postcodes(mock_http)
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/street-proof?radius_m=10")
    assert res.status_code == 400, res.text
    assert res.json()["code"] == "validation"


def test_route_works_logged_out_on_a_demo_home_even_with_no_token(client, mock_http) -> None:
    """No nearby postcodes (and no EPC token) -> an empty, never-500 result."""
    _mock_nearest_postcodes(mock_http)
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/street-proof")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["peers_count"] == 0
    assert "uprn" not in res.text
