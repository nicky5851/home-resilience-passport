"""S14: indexing maths, < 5 comps -> HPI method, no house numbers/full postcodes in the
response, uplift never negative, target <= current -> 0, offline."""

import re

import httpx
import pytest

from app.studio.features.s14_green_value_lens.config import HPI_BASE, PPD_BASE
from app.studio.features.s14_green_value_lens.hpi import region_slug
from app.studio.features.s14_green_value_lens.service import (
    band_steps,
    indexed_price,
    median_and_iqr,
    uplift_gbp,
)

API = "/api/v1"


def test_indexed_price_scales_by_the_index_ratio() -> None:
    assert indexed_price(100_000, index_at_sale=100, index_latest=110) == 110_000
    assert indexed_price(100_000, index_at_sale=50, index_latest=100) == 200_000


def test_median_and_iqr_rounds_to_nearest_1000() -> None:
    median, q1, q3 = median_and_iqr([201_200, 198_700, 250_300, 180_900, 300_100])
    assert median % 1000 == 0
    assert q1 <= median <= q3


def test_band_steps_target_at_or_below_current_is_zero() -> None:
    assert band_steps("D", "D") == 0
    assert band_steps("D", "E") == 0  # target worse than current
    assert band_steps("D", "B") == 2
    assert band_steps(None, "B") == 0


def test_uplift_never_negative() -> None:
    low, high = uplift_gbp("D", "B", 300_000, premium_pct_low=0.8, premium_pct_high=1.7)
    assert low is not None and low >= 0
    assert high is not None and high >= 0

    low0, high0 = uplift_gbp("D", "E", 300_000, premium_pct_low=0.8, premium_pct_high=1.7)
    assert low0 == 0 and high0 == 0


def test_region_slug() -> None:
    assert region_slug("Crawley") == "crawley"


def _mock_everything_offline(mock_http) -> None:
    mock_http.get(url__startswith=HPI_BASE).mock(side_effect=httpx.ConnectError("offline"))
    mock_http.get(url__startswith=PPD_BASE).mock(side_effect=httpx.ConnectError("offline"))
    from app.adapters.postcodes import POSTCODES_IO_URL

    mock_http.get(url__startswith=POSTCODES_IO_URL.removesuffix("/")).mock(
        side_effect=httpx.ConnectError("offline")
    )


def test_route_falls_back_to_hpi_average_offline(client, mock_http) -> None:
    _mock_everything_offline(mock_http)
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/green-value")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["method"] == "hpi_average"
    assert body["comparables_count"] < 5


def test_route_response_has_no_house_numbers_or_full_postcodes(client, mock_http) -> None:
    _mock_everything_offline(mock_http)
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/green-value")
    assert res.status_code == 200, res.text
    text = res.text
    assert not re.search(r"\b[A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2}\b", text)


def test_route_has_at_least_two_cited_premium_sources(client, mock_http) -> None:
    _mock_everything_offline(mock_http)
    res = client.get(f"{API}/studio/homes/demo-clay-semi/green-value?target_band=B")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["premium_sources"]) >= 2
    assert all(p["url"].startswith("http") for p in body["premium_sources"])


@pytest.fixture
def ppd_and_hpi_apis(mock_http):
    from app.adapters.postcodes import POSTCODES_IO_URL

    def postcodes_io_answer(request: httpx.Request) -> httpx.Response:
        if request.url.path.rstrip("/").endswith("postcodes"):
            return httpx.Response(200, json={"status": 200, "result": [{"postcode": "RH10 1SB"}]})
        return httpx.Response(
            200,
            json={
                "status": 200,
                "result": {
                    "postcode": "RH10 1SB",
                    "latitude": 51.11,
                    "longitude": -0.19,
                    "admin_district": "Crawley",
                    "country": "England",
                    "region": "South East",
                },
            },
        )

    mock_http.get(url__startswith=POSTCODES_IO_URL.removesuffix("/")).mock(
        side_effect=postcodes_io_answer
    )

    hpi_body = {"primaryTopic": {"housePriceIndexTerraced": 110.0, "averagePriceTerraced": 300_000}}
    mock_http.get(url__startswith=HPI_BASE).mock(return_value=httpx.Response(200, json=hpi_body))
    sale_item = {
        "pricePaid": 250_000,
        "transactionDate": "Mon, 01 Jan 2024",
        "propertyType": {"_about": "http://landregistry.data.gov.uk/def/common/terraced"},
        "transactionCategory": {
            "_about": "http://landregistry.data.gov.uk/def/ppi/standardPricePaidTransaction"
        },
    }
    ppd_body = {"result": {"items": [sale_item] * 6}}
    mock_http.get(url__startswith=PPD_BASE).mock(return_value=httpx.Response(200, json=ppd_body))


def test_route_uses_comparables_when_enough_sales(client, ppd_and_hpi_apis) -> None:
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/green-value")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["method"] == "comparables"
    assert body["comparables_count"] >= 5
