"""S00: Studio's hub — feature list, home resolver, shared OpenAPI stays untouched."""

import json
import uuid

from app.config import REPO_ROOT
from tests.conftest import DEMO_SLUGS

API = "/api/v1"
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


def _create_home(user_client) -> str:
    from tests.conftest import load_fixture

    household = load_fixture("city-top-flat")["household"]
    body = {"address": WESTMINSTER, "household": household, "property_override": FLAT}
    res = user_client.post(f"{API}/homes", json=body)
    assert res.status_code == 201, res.text
    return res.json()["home_id"]


def test_features_list_is_public_and_a_list(client) -> None:
    res = client.get(f"{API}/studio/features")
    assert res.status_code == 200, res.text
    assert isinstance(res.json(), list)


def test_demo_home_summary_needs_no_login(client) -> None:
    res = client.get(f"{API}/studio/homes/demo-{DEMO_SLUGS[0]}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["is_demo"] is True
    assert body["line1"].startswith("Demo")
    assert body["score"]["value"] is not None


def test_unknown_demo_slug_is_404(client) -> None:
    res = client.get(f"{API}/studio/homes/demo-does-not-exist")
    assert res.status_code == 404, res.text
    assert res.json()["code"] == "not_found"


def test_uuid_ref_needs_login(client) -> None:
    res = client.get(f"{API}/studio/homes/{uuid.uuid4()}")
    assert res.status_code == 401, res.text


def test_unknown_home_id_is_404_when_logged_in(user_client) -> None:
    res = user_client.get(f"{API}/studio/homes/{uuid.uuid4()}")
    assert res.status_code == 404, res.text


def test_owner_sees_their_real_home(user_client) -> None:
    home_id = _create_home(user_client)
    user_client.post(f"{API}/homes/{home_id}/assess")

    res = user_client.get(f"{API}/studio/homes/{home_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["is_demo"] is False
    assert body["line1"] == "1 Test Street"
    assert body["postcode_district"] == "SW1A"


def test_other_users_cannot_see_someone_elses_home(client, user_client) -> None:
    from tests.conftest import log_in

    home_id = _create_home(user_client)
    user_client.post(f"{API}/homes/{home_id}/assess")

    log_in(client, "someone-else@example.com")
    res = client.get(f"{API}/studio/homes/{home_id}")
    assert res.status_code == 404, res.text


def test_shared_openapi_is_unaffected_by_studio() -> None:
    """Studio is mounted with include_in_schema=False (spec §1.4): the shared schema must not
    gain `/studio` paths just because `app.studio.router` is imported."""
    path = REPO_ROOT / "docs" / "openapi.json"
    spec = json.loads(path.read_text())
    assert all(not p.startswith("/api/v1/studio") for p in spec["paths"])


def test_studio_has_its_own_openapi_snapshot() -> None:
    path = REPO_ROOT / "docs" / "openapi-studio.json"
    assert path.exists()
    spec = json.loads(path.read_text())
    assert "/api/v1/studio/features" in spec["paths"]
    assert "/api/v1/studio/homes/{ref}" in spec["paths"]
