"""Seam 3: every route in spec §4.2 exists and answers schema-valid JSON (foundation stub)."""

import io
import uuid
from datetime import date, timedelta

import pytest
from pydantic import TypeAdapter

from app.config import UPLOAD_MAX_BYTES
from app.main import app
from app.schemas import DemoHome, FundingBundle, Passport, PassportEvent, Plan, PublicPassport
from app.schemas.api import (
    Assessment,
    ErrorBody,
    HomeCreated,
    HomeSummary,
    ModelInfo,
    PostcodeLookup,
    ShareLink,
)
from tests.conftest import load_fixture

API = "/api/v1"
PDF = b"%PDF-1.4\n%stub\n"

SPEC_ROUTES = {
    ("GET", "/health"),
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("POST", "/auth/logout"),
    ("POST", "/auth/forgot-password"),
    ("POST", "/auth/reset-password"),
    ("GET", "/users/me"),
    ("GET", "/users/me/export"),
    ("DELETE", "/users/me"),
    ("GET", "/lookup/postcode/{postcode}"),
    ("POST", "/homes"),
    ("GET", "/homes"),
    ("DELETE", "/homes/{home_id}"),
    ("POST", "/homes/{home_id}/assess"),
    ("GET", "/homes/{home_id}/risk"),
    ("POST", "/homes/{home_id}/plan"),
    ("POST", "/homes/{home_id}/funding"),
    ("GET", "/homes/{home_id}/passport"),
    ("POST", "/homes/{home_id}/work"),
    ("GET", "/homes/{home_id}/work/{event_id}/certificate"),
    ("POST", "/homes/{home_id}/share"),
    ("DELETE", "/homes/{home_id}/share"),
    ("GET", "/public/passport/{share_token}"),
    ("GET", "/model/info"),
    ("GET", "/demo/homes"),
}


def _new_home(client, slug: str = "flood-terrace") -> str:
    f = load_fixture(slug)
    body = {"address": f["address"], "household": f["household"], "property_override": None}
    res = client.post(f"{API}/homes", json=body)
    assert res.status_code == 201, res.text
    return str(HomeCreated.model_validate(res.json()).home_id)


def test_every_spec_route_exists() -> None:
    paths = app.openapi()["paths"]
    have = {(m.upper(), p.removeprefix(API)) for p, ops in paths.items() for m in ops}
    assert SPEC_ROUTES <= have, SPEC_ROUTES - have


def test_demo_homes(client) -> None:
    res = client.get(f"{API}/demo/homes")
    assert res.status_code == 200
    homes = TypeAdapter(list[DemoHome]).validate_python(res.json())
    assert len(homes) == 5


def test_model_info(client) -> None:
    ModelInfo.model_validate(client.get(f"{API}/model/info").json())


def test_lookup_demo_postcode_any_format(client) -> None:
    res = client.get(f"{API}/lookup/postcode/yo19tj")
    assert res.status_code == 200
    body = PostcodeLookup.model_validate(res.json())
    assert body.postcode == "YO1 9TJ" and len(body.addresses) == 1


def test_lookup_unknown_postcode_has_empty_list(client) -> None:
    body = PostcodeLookup.model_validate(client.get(f"{API}/lookup/postcode/SW1A1AA").json())
    assert body.addresses == []


@pytest.mark.parametrize("pc", ["EH1 1YZ", "BT1 1AA", "G1 1XQ"])
def test_lookup_scotland_ni_unsupported(client, pc: str) -> None:
    res = client.get(f"{API}/lookup/postcode/{pc}")
    assert res.status_code == 400
    assert res.json() == {
        "detail": "Home Resilience Passport covers England and Wales for now.",
        "code": "unsupported_region",
    }


def test_lookup_bad_postcode(client) -> None:
    res = client.get(f"{API}/lookup/postcode/nonsense")
    assert res.status_code == 400
    ErrorBody.model_validate(res.json())
    assert res.json()["code"] == "validation"


def test_full_home_journey(user_client) -> None:
    c = user_client
    home_id = _new_home(c, "city-top-flat")

    assert c.get(f"{API}/homes/{home_id}/risk").status_code == 404  # before assessment

    a = Assessment.model_validate(c.post(f"{API}/homes/{home_id}/assess").json())
    assert [lv.hazard for lv in a.risk.levels][0] == "river_sea_flood"
    Assessment.model_validate(c.get(f"{API}/homes/{home_id}/risk").json())

    homes = TypeAdapter(list[HomeSummary]).validate_python(c.get(f"{API}/homes").json())
    assert [str(h.home_id) for h in homes] == [home_id] and homes[0].score is not None

    plan = Plan.model_validate(c.post(f"{API}/homes/{home_id}/plan").json())
    Plan.model_validate(c.post(f"{API}/homes/{home_id}/plan", json={"budget_gbp": 900}).json())
    ids = [i.measure.id for i in plan.items if i.selected]
    res = c.post(f"{API}/homes/{home_id}/funding", json={"selected_ids": ids})
    FundingBundle.model_validate(res.json())

    passport = Passport.model_validate(c.get(f"{API}/homes/{home_id}/passport").json())
    assert str(passport.home_id) == home_id
    assert [e.kind for e in passport.events][-1] == "assessed"

    assert c.delete(f"{API}/homes/{home_id}").status_code == 204
    assert c.get(f"{API}/homes/{home_id}/passport").status_code == 404


def test_validation_error_is_400_with_string_detail(user_client) -> None:
    res = user_client.post(f"{API}/homes", json={"address": {}})
    assert res.status_code == 400
    body = res.json()
    assert body["code"] == "validation" and isinstance(body["detail"], str)


def test_unknown_home_404(user_client) -> None:
    res = user_client.get(f"{API}/homes/{uuid.uuid4()}/passport")
    assert res.status_code == 404
    assert res.json()["code"] == "not_found"


def test_other_users_home_404(client) -> None:
    client.post(f"{API}/auth/login", data={"username": "owner@example.com", "password": "x"})
    home_id = _new_home(client)
    client.post(f"{API}/auth/login", data={"username": "other@example.com", "password": "x"})
    assert client.get(f"{API}/homes/{home_id}/passport").status_code == 404


def test_unknown_route_404_contract_shape(client) -> None:
    res = client.get(f"{API}/nope")
    assert res.status_code == 404
    assert res.json() == {"detail": "We couldn't find that.", "code": "not_found"}


def test_work_upload_and_certificate(user_client) -> None:
    c = user_client
    home_id = _new_home(c)
    measure = load_fixture("flood-terrace")["plan"]["items"][0]["measure"]["id"]
    res = c.post(
        f"{API}/homes/{home_id}/work",
        data={"measure_id": measure, "completed_on": date.today().isoformat(), "cost_gbp": "120"},
        files={"certificate": ("my cert.pdf", io.BytesIO(PDF), "application/octet-stream")},
    )
    assert res.status_code == 200, res.text
    ev = PassportEvent.model_validate(res.json())
    assert ev.kind == "work_recorded"
    assert ev.detail == {
        "measure_id": measure,
        "completed_on": date.today().isoformat(),
        "cost_gbp": 120,
        "has_certificate": True,
        "certificate_name": "my cert.pdf",
    }
    cert = c.get(f"{API}/homes/{home_id}/work/{ev.id}/certificate")
    assert cert.status_code == 200 and cert.content == PDF
    assert cert.headers["content-type"] == "application/pdf"


def test_work_rejects_wrong_type_by_content(user_client) -> None:
    home_id = _new_home(user_client)
    res = user_client.post(
        f"{API}/homes/{home_id}/work",
        data={"measure_id": "flood-door", "completed_on": "2026-01-01"},
        files={"certificate": ("virus.pdf", io.BytesIO(b"MZ\x90\x00"), "application/pdf")},
    )
    assert res.status_code == 415
    assert res.json()["code"] == "unsupported_file"


def test_work_rejects_large_file(user_client) -> None:
    home_id = _new_home(user_client)
    big = PDF + b"0" * UPLOAD_MAX_BYTES
    res = user_client.post(
        f"{API}/homes/{home_id}/work",
        data={"measure_id": "flood-door", "completed_on": "2026-01-01"},
        files={"certificate": ("big.pdf", io.BytesIO(big), "application/pdf")},
    )
    assert res.status_code == 413
    assert res.json()["code"] == "file_too_large"


def test_work_rejects_future_date(user_client) -> None:
    home_id = _new_home(user_client)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    res = user_client.post(
        f"{API}/homes/{home_id}/work", data={"measure_id": "flood-door", "completed_on": tomorrow}
    )
    assert res.status_code == 400


def test_share_public_and_revoke(user_client) -> None:
    c = user_client
    home_id = _new_home(c)
    c.post(
        f"{API}/homes/{home_id}/work",
        data={"measure_id": "flood-door", "completed_on": "2026-01-01"},
        files={"certificate": ("c.pdf", io.BytesIO(PDF))},
    )
    link = ShareLink.model_validate(c.post(f"{API}/homes/{home_id}/share").json())
    assert len(link.share_token) == 32 and link.url.endswith(f"/p/{link.share_token}")

    c.cookies.clear()  # logged out
    res = c.get(f"{API}/public/passport/{link.share_token}")
    assert res.status_code == 200
    body = res.json()
    PublicPassport.model_validate(body)
    assert "household" not in body and "share_token" not in body
    work = [e for e in body["events"] if e["kind"] == "work_recorded"]
    assert work and work[0]["detail"]["has_certificate"] is True
    assert "certificate_name" not in work[0]["detail"]

    c.post(f"{API}/auth/login", data={"username": "a@example.com", "password": "x"})
    assert c.delete(f"{API}/homes/{home_id}/share").status_code == 204
    res = c.get(f"{API}/public/passport/{link.share_token}")
    assert res.status_code == 404
    assert res.json()["detail"] == "This link is no longer active."


def test_openapi_lists_error_shape() -> None:
    schemas = app.openapi()["components"]["schemas"]
    assert "ErrorBody" in schemas
