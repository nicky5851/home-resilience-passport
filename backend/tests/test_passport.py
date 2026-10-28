"""N14: passport, work records with certificates in storage, and share links."""

import io
import uuid
from datetime import date

import pytest

from app.schemas import Passport, PassportEvent, PublicPassport, ResilienceScore
from app.services import assessment, passport, storage
from tests.conftest import load_fixture, log_in

API = "/api/v1"
PDF = b"%PDF-1.4\n%work certificate\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def _home(client, assess: bool = True) -> str:
    f = load_fixture("flood-terrace")
    body = {"address": f["address"], "household": f["household"], "property_override": None}
    home_id = client.post(f"{API}/homes", json=body).json()["home_id"]
    if assess:
        assert client.post(f"{API}/homes/{home_id}/assess").status_code == 200
    return home_id


def _work(client, home_id: str, measure_id: str = "flood-door", file=None, **extra):
    data = {"measure_id": measure_id, "completed_on": date.today().isoformat(), **extra}
    files = {"certificate": file} if file else None
    return client.post(f"{API}/homes/{home_id}/work", data=data, files=files)


@pytest.fixture
def points_per_measure(monkeypatch):
    """L's `compute_score` is still the stub (always 50) until L5: 50 + 5 per completed measure."""

    def fake(risk, prop, completed=()):
        stub = ResilienceScore.model_validate(load_fixture("flood-terrace")["score"])
        value = stub.value + 5 * len(completed)
        return stub.model_copy(update={"value": value})

    monkeypatch.setattr(passport, "compute_score", fake)
    monkeypatch.setattr(assessment, "compute_score", fake)


# --- Work raises the score ---------------------------------------------------------------------


def test_recording_work_raises_the_score_and_adds_an_event(user_client, points_per_measure) -> None:
    c = user_client
    home_id = _home(c)
    before = Passport.model_validate(c.get(f"{API}/homes/{home_id}/passport").json())

    res = _work(c, home_id, cost_gbp="2400")
    assert res.status_code == 200, res.text
    event = PassportEvent.model_validate(res.json())
    assert event.kind == "work_recorded" and event.score_after == before.latest_score.value + 5
    assert event.detail == {
        "measure_id": "flood-door", "completed_on": date.today().isoformat(), "cost_gbp": 2400,
        "has_certificate": False, "certificate_name": None,
    }  # fmt: skip

    after = Passport.model_validate(c.get(f"{API}/homes/{home_id}/passport").json())
    assert after.latest_score.value == before.latest_score.value + 5
    assert after.events[-1].id == event.id  # score history: the events' score_after
    assert c.get(f"{API}/homes").json()[0]["score"]["value"] == after.latest_score.value

    # Assessing again keeps the work counted.
    again = c.post(f"{API}/homes/{home_id}/assess").json()
    assert again["score"]["value"] == after.latest_score.value


def test_passport_assembles_the_home(user_client) -> None:
    c = user_client
    home_id = _home(c, assess=False)
    res = c.get(f"{API}/homes/{home_id}/passport")
    assert res.status_code == 404 and res.json()["code"] == "not_found"  # assess first

    c.post(f"{API}/homes/{home_id}/assess")
    p = Passport.model_validate(c.get(f"{API}/homes/{home_id}/passport").json())
    f = load_fixture("flood-terrace")
    assert p.address.postcode == f["address"]["postcode"]
    assert p.household.model_dump(mode="json") == f["household"]
    assert p.plan is None and p.share_token is None
    assert [e.kind for e in p.events] == ["assessed"]

    plan = c.post(f"{API}/homes/{home_id}/plan").json()
    p = Passport.model_validate(c.get(f"{API}/homes/{home_id}/passport").json())
    assert p.plan is not None and p.plan.model_dump(mode="json") == plan  # the saved plan


# --- Certificates (CONTRACT §6) -----------------------------------------------------------------


def test_certificate_is_stored_under_a_random_name(user_client, upload_dir) -> None:
    c = user_client
    home_id = _home(c)
    res = _work(c, home_id, file=("Invoice from Bob's Builders.pdf", io.BytesIO(PDF)))
    event = PassportEvent.model_validate(res.json())
    assert event.detail["has_certificate"] is True
    assert event.detail["certificate_name"] == "Invoice from Bob's Builders.pdf"

    [stored] = list(upload_dir.iterdir())
    assert storage.KEY.fullmatch(stored.name) and stored.suffix == ".pdf"
    assert stored.read_bytes() == PDF

    got = c.get(f"{API}/homes/{home_id}/work/{event.id}/certificate")
    assert got.status_code == 200 and got.content == PDF
    assert got.headers["content-type"] == "application/pdf"


def test_png_keeps_its_type(user_client, upload_dir) -> None:
    home_id = _home(user_client)
    event = _work(user_client, home_id, file=("photo.PDF", io.BytesIO(PNG), "application/pdf"))
    assert [p.suffix for p in upload_dir.iterdir()] == [".png"]  # first bytes, not the name
    got = user_client.get(f"{API}/homes/{home_id}/work/{event.json()['id']}/certificate")
    assert got.headers["content-type"] == "image/png"


def test_renamed_exe_is_refused(user_client, upload_dir) -> None:
    home_id = _home(user_client)
    exe = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64
    res = _work(user_client, home_id, file=("invoice.pdf", io.BytesIO(exe), "application/pdf"))
    assert res.status_code == 415 and res.json()["code"] == "unsupported_file"
    assert not upload_dir.exists() or not any(upload_dir.iterdir())
    p = user_client.get(f"{API}/homes/{home_id}/passport").json()
    assert [e["kind"] for e in p["events"]] == ["assessed"]  # nothing recorded


def test_six_megabyte_pdf_is_refused(user_client) -> None:
    home_id = _home(user_client)
    big = PDF + b"0" * (6 * 1024 * 1024)
    res = _work(user_client, home_id, file=("big.pdf", io.BytesIO(big)))
    assert res.status_code == 413 and res.json()["code"] == "file_too_large"


def test_long_file_names_are_cut_to_100_characters(user_client) -> None:
    home_id = _home(user_client)
    res = _work(user_client, home_id, file=("a" * 150 + ".pdf", io.BytesIO(PDF)))
    assert len(res.json()["detail"]["certificate_name"]) == 100


def test_another_user_gets_404_on_your_certificate(client) -> None:
    log_in(client, "owner@example.com")
    home_id = _home(client)
    event_id = _work(client, home_id, file=("c.pdf", io.BytesIO(PDF))).json()["id"]
    url = f"{API}/homes/{home_id}/work/{event_id}/certificate"
    assert client.get(url).status_code == 200

    log_in(client, "other@example.com")
    assert client.get(url).status_code == 404
    other_home = _home(client)  # their own home id with your event id: still 404
    res = client.get(f"{API}/homes/{other_home}/work/{event_id}/certificate")
    assert res.status_code == 404

    client.cookies.clear()
    assert client.get(url).status_code == 401


def test_unknown_certificate_is_404(user_client) -> None:
    home_id = _home(user_client)
    event_id = _work(user_client, home_id).json()["id"]  # work without a file
    for eid in (event_id, uuid.uuid4()):
        res = user_client.get(f"{API}/homes/{home_id}/work/{eid}/certificate")
        assert res.status_code == 404


def test_deleting_a_home_removes_its_files(user_client, upload_dir) -> None:
    home_id = _home(user_client)
    _work(user_client, home_id, file=("c.pdf", io.BytesIO(PDF)))
    _work(user_client, home_id, measure_id="flood-door", file=("d.png", io.BytesIO(PNG)))
    assert len(list(upload_dir.iterdir())) == 2
    assert user_client.delete(f"{API}/homes/{home_id}").status_code == 204
    assert list(upload_dir.iterdir()) == []


def test_deleting_the_account_removes_its_files(client, upload_dir) -> None:
    log_in(client, "leaver@example.com")
    for _ in range(2):
        _work(client, _home(client), file=("c.pdf", io.BytesIO(PDF)))
    log_in(client, "stayer@example.com")
    _work(client, _home(client), file=("keep.pdf", io.BytesIO(PDF)))
    assert len(list(upload_dir.iterdir())) == 3

    log_in(client, "leaver@example.com")
    assert client.delete(f"{API}/users/me").status_code == 204
    assert len(list(upload_dir.iterdir())) == 1  # only the other user's file is left


def test_storage_keys_cannot_escape_the_folder(tmp_path) -> None:
    s = storage.LocalStorage(tmp_path)
    for key in ("../x.pdf", "/etc/passwd", "a.pdf", f"{uuid.uuid4().hex}.exe"):
        with pytest.raises(ValueError):
            s.put(key, b"x")
    key = storage.new_key("pdf")
    s.put(key, PDF)
    assert s.get(key) == PDF
    s.delete(key)
    assert s.get(key) is None
    s.delete(key)  # deleting twice is fine


# --- Sharing ----------------------------------------------------------------------------------


def test_share_link_public_and_revoked(user_client) -> None:
    c = user_client
    home_id = _home(c)
    _work(c, home_id, file=("Private name.pdf", io.BytesIO(PDF)))
    link = c.post(f"{API}/homes/{home_id}/share").json()
    token = link["share_token"]
    assert len(token) == 32
    assert Passport.model_validate(c.get(f"{API}/homes/{home_id}/passport").json()).share_token

    c.cookies.clear()  # logged out
    res = c.get(f"{API}/public/passport/{token}")
    assert res.status_code == 200
    body = res.json()
    PublicPassport.model_validate(body)
    assert "household" not in body and "share_token" not in body
    assert "Private name" not in res.text  # no certificate names
    work = next(e for e in body["events"] if e["kind"] == "work_recorded")
    assert work["detail"]["has_certificate"] is True

    log_in(c, "a@example.com")
    new = c.post(f"{API}/homes/{home_id}/share").json()["share_token"]  # a new link…
    c.cookies.clear()
    assert c.get(f"{API}/public/passport/{token}").status_code == 404  # …ends the old one
    log_in(c, "a@example.com")
    assert c.delete(f"{API}/homes/{home_id}/share").status_code == 204
    c.cookies.clear()
    assert c.get(f"{API}/public/passport/{new}").status_code == 404
