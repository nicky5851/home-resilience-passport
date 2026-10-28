"""N15: the five demo homes end to end with Wi-Fi off, and upstream timeouts never crash."""

import asyncio
import io
import logging

import httpx
import pytest

from app.adapters import climate, postcodes
from app.db.seed import seed_demo_cache
from app.schemas import Passport, PassportEvent, PublicPassport
from app.schemas.api import Assessment
from tests.conftest import DEMO_SLUGS, load_fixture, log_in

API = "/api/v1"
PDF = b"%PDF-1.4\n%demo\n"
CLIMATE_FIELDS = (
    "hot_days_baseline", "hot_days_2050", "heavy_rain_days_baseline", "heavy_rain_days_2050",
    "max_wind_baseline_kmh", "max_wind_2050_kmh",
)  # fmt: skip


def _cut_off(mock_http, error: Exception) -> None:
    """Every outbound request fails with `error`, including the routes other fixtures mocked."""
    for route in mock_http.routes:
        route.side_effect = error
    mock_http.route().mock(side_effect=error)


@pytest.fixture
def wifi_off(client, mock_http, memory_cache):
    """`make seed` has run (demo data in the cache), then the network goes away."""
    asyncio.run(seed_demo_cache(memory_cache))
    _cut_off(mock_http, httpx.ConnectError("Wi-Fi off"))
    log_in(client, "demo@example.com")
    return client


def test_seed_caches_each_demo_home(memory_cache) -> None:
    assert asyncio.run(seed_demo_cache(memory_cache)) == 5
    for slug in DEMO_SLUGS:
        a = load_fixture(slug)["address"]
        assert asyncio.run(memory_cache.get(postcodes.cache_key(a["postcode"])))["region"]
        for years in ((1991, 2020), (2041, 2050)):
            assert asyncio.run(memory_cache.get(climate.period_key(a["lat"], a["lon"], years)))


@pytest.mark.parametrize("slug", DEMO_SLUGS)
def test_demo_home_from_the_list_offline(wifi_off, slug) -> None:
    """The demo list → a demo home → every screen and action, from the fixtures."""
    c = wifi_off
    demo = next(d for d in c.get(f"{API}/demo/homes").json() if d["slug"] == slug)
    f = load_fixture(slug)
    home = f"{API}/homes/{f['passport']['home_id']}"
    assert c.post(f"{home}/assess").json()["score"] == f["score"]
    assert c.get(f"{home}/risk").status_code == 200
    plan = c.post(f"{home}/plan").json()
    assert c.post(f"{home}/funding", json={"selected_ids": []}).status_code == 200
    measure = plan["items"][0]["measure"]["id"]
    work = c.post(
        f"{home}/work",
        data={"measure_id": measure, "completed_on": "2026-01-01"},
        files={"certificate": ("c.pdf", io.BytesIO(PDF))},
    )
    event = PassportEvent.model_validate(work.json())
    assert c.get(f"{home}/work/{event.id}/certificate").content == PDF
    Passport.model_validate(c.get(f"{home}/passport").json())
    token = c.post(f"{home}/share").json()["share_token"]
    PublicPassport.model_validate(c.get(f"{API}/public/passport/{token}").json())
    assert c.delete(f"{home}/share").status_code == 204
    assert c.delete(home).status_code == 404  # demo homes can't be deleted
    assert demo["address"]["postcode"] == f["address"]["postcode"]


@pytest.mark.parametrize("slug", DEMO_SLUGS)
def test_demo_address_journey_offline(wifi_off, slug) -> None:
    """Typing a demo postcode: lookup → add the home → assess → plan → work → share."""
    c = wifi_off
    f = load_fixture(slug)
    a = f["address"]
    look = c.get(f"{API}/lookup/postcode/{a['postcode']}")
    assert look.status_code == 200, look.text
    assert look.json()["addresses"][0]["line1"] == a["line1"]

    body = {"address": a, "household": f["household"], "property_override": None}
    home = f"{API}/homes/{c.post(f'{API}/homes', json=body).json()['home_id']}"
    res = c.post(f"{home}/assess")
    assert res.status_code == 200, res.text
    inputs = Assessment.model_validate(res.json()).inputs
    # The seeded climate figures, not the regional defaults; no live warnings offline.
    assert {k: getattr(inputs, k) for k in CLIMATE_FIELDS} == {
        k: f["inputs"][k] for k in CLIMATE_FIELDS
    }
    assert inputs.active_flood_warnings == 0

    plan = c.post(f"{home}/plan").json()
    assert plan["explanation_source"] == "template"  # no LLM offline
    measure = plan["items"][0]["measure"]["id"]
    assert c.post(
        f"{home}/work", data={"measure_id": measure, "completed_on": "2026-01-01"}
    ).is_success
    token = c.post(f"{home}/share").json()["share_token"]
    c.cookies.clear()
    assert c.get(f"{API}/public/passport/{token}").status_code == 200


def test_upstream_timeouts_are_logged_not_crashing(client, mock_http, caplog) -> None:
    """Every data source times out: a non-demo postcode is 502, a home still assesses."""
    _cut_off(mock_http, httpx.ReadTimeout("slow"))
    log_in(client, "slow@example.com")
    caplog.set_level(logging.WARNING)

    res = client.get(f"{API}/lookup/postcode/SW1A 1AA")
    assert res.status_code == 502 and res.json()["code"] == "upstream_unavailable"

    f = load_fixture("city-top-flat")
    address = f["address"] | {"postcode": "SW1A 1AA", "uprn": "100023336956"}
    body = {"address": address, "household": f["household"], "property_override": None}
    res = client.post(f"{API}/homes", json=body)
    assert res.status_code == 400  # EPC register down and no details: ask for them
    prop = {"property_type": "flat", "source": "user"}
    home_id = client.post(f"{API}/homes", json=body | {"property_override": prop}).json()["home_id"]
    res = client.post(f"{API}/homes/{home_id}/assess")
    assert res.status_code == 200
    assert res.json()["inputs"]["hot_days_2050"] is not None  # regional defaults

    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "EPC register unavailable" in logged and "Open-Meteo unavailable" in logged


def test_errors_share_one_shape(user_client, monkeypatch, caplog) -> None:
    """CONTRACT §3: every error is `{detail, code}`, unexpected ones included (500 internal)."""
    from fastapi.testclient import TestClient

    from ml import predict

    f = load_fixture("flood-terrace")
    home = f"{API}/homes/{f['passport']['home_id']}"
    bad_work = {"measure_id": "x", "completed_on": "2026-01-01"}
    cases = [
        (user_client.post(f"{home}/work", data=bad_work), 400, "validation"),
        (user_client.get(f"{API}/homes/not-a-uuid/risk"), 400, "validation"),
        (user_client.get(f"{API}/no-such-route"), 404, "not_found"),
    ]  # fmt: skip

    def boom():
        raise RuntimeError("unexpected")

    monkeypatch.setattr(predict, "info", boom)
    caplog.set_level(logging.ERROR)
    with TestClient(user_client.app, raise_server_exceptions=False) as raw:
        cases.append((raw.get(f"{API}/model/info"), 500, "internal"))
    for res, status, code in cases:
        assert (res.status_code, res.json()["code"]) == (status, code), res.text
        assert set(res.json()) == {"detail", "code"} and res.json()["detail"]
    assert "unexpected" not in cases[-1][0].text  # no internals in the answer
    assert "Unhandled error: RuntimeError" in caplog.text
