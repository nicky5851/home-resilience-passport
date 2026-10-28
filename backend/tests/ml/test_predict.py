"""N13: EPC estimates in the assessment and `/model/info`."""

import statistics
import time

import pytest

from app.schemas import Address, PropertyFacts
from app.schemas.api import Assessment, ModelInfo
from app.services import assessment
from ml import predict
from ml.features import BANDS
from tests.conftest import DEMO_SLUGS, load_fixture

API = "/api/v1"
pytestmark = pytest.mark.anyio
USER_FLAT = PropertyFacts(property_type="flat", floor_level=2, top_floor=True, source="user")


@pytest.fixture
def no_region(monkeypatch):
    async def region(postcode, cache):
        return "London"

    monkeypatch.setattr(assessment, "_region", region)


def _address(slug: str = "city-top-flat") -> Address:
    return Address.model_validate(load_fixture(slug)["address"])


@pytest.mark.parametrize("slug", DEMO_SLUGS)
def test_demo_home_without_its_epc_gets_an_estimate_fast(slug) -> None:
    prop = PropertyFacts.model_validate(load_fixture(slug)["property"])
    stripped = prop.model_copy(update={"epc_rating": None, "co2_tonnes_per_year": None})
    predict.estimate(stripped, "London")  # warm up
    times = []
    for _ in range(5):  # median, so one GC pause on a busy CI runner doesn't fail the test
        start = time.perf_counter()
        est = predict.estimate(stripped, "London")
        times.append(time.perf_counter() - start)
    assert statistics.median(times) < 0.05  # spec N13: under 50 ms (about 5 ms here)
    assert est is not None and est.band in BANDS and 0 <= est.co2_tonnes_per_year < 50


async def test_missing_band_is_estimated_and_labelled(no_region) -> None:
    out = await assessment.with_estimate(USER_FLAT, _address(), cache=None)
    assert out.source == "model"
    assert out.epc_rating in BANDS and out.co2_tonnes_per_year is not None
    assert out.top_floor is True and out.floor_level == 2  # the user's facts are kept


async def test_a_certificate_is_never_replaced(no_region) -> None:
    cert = USER_FLAT.model_copy(update={"epc_rating": "G", "source": "epc_api"})
    assert await assessment.with_estimate(cert, _address(), cache=None) is cert


async def test_known_co2_is_kept(no_region) -> None:
    prop = USER_FLAT.model_copy(update={"co2_tonnes_per_year": 9.9})
    out = await assessment.with_estimate(prop, _address(), cache=None)
    assert out.co2_tonnes_per_year == 9.9 and out.source == "model"


async def test_no_model_file_leaves_the_facts(no_region, monkeypatch) -> None:
    monkeypatch.setattr(predict, "model", lambda: None)
    assert await assessment.with_estimate(USER_FLAT, _address(), cache=None) is USER_FLAT
    assert predict.info()["version"] == "unavailable"


def test_estimate_reaches_the_api_response(user_client) -> None:
    """A home without a certificate: the assessment says `source: "model"` (offline client)."""
    f = load_fixture("city-top-flat")
    body = {
        "address": f["address"] | {"uprn": None},
        "household": f["household"],
        "property_override": USER_FLAT.model_dump(),
    }
    home_id = user_client.post(f"{API}/homes", json=body).json()["home_id"]
    a = Assessment.model_validate(user_client.post(f"{API}/homes/{home_id}/assess").json())
    assert a.inputs.property.source == "model"
    assert a.inputs.property.epc_rating in BANDS
    risk = user_client.get(f"{API}/homes/{home_id}/risk").json()
    assert risk["inputs"]["property"]["source"] == "model"  # stored as estimated


def test_model_info(client) -> None:
    info = ModelInfo.model_validate(client.get(f"{API}/model/info").json())
    assert info.version.startswith("epc-")
    assert "London" in info.trained_on
    assert info.metrics["within_one_band"] >= 0.8
    assert "by_region.London.accuracy" in info.metrics
