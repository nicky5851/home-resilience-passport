"""S17: first-frost computation, oil-tank-only-for-oil rules, ICS line length/CRLF, revoked
token -> 404, no postcode in the feed, and offline."""

import re
import uuid
from datetime import date, datetime

import httpx
import pytest

from app.studio.features.s17_care_calendar.climatology import (
    ClimateDay,
    first_and_last_frost,
    wettest_month,
    windiest_month,
)
from app.studio.features.s17_care_calendar.config import ARCHIVE_URL
from app.studio.features.s17_care_calendar.ics import fold_line, write_ics
from app.studio.features.s17_care_calendar.tasks import TaskContext, condition_met, resolve_month
from tests.conftest import load_fixture

API = "/api/v1"


def _winter_series(first_frost_days: list[tuple[int, int, int]]) -> list[ClimateDay]:
    """One `ClimateDay` per season in `first_frost_days`, each a single frost day at
    (year, month, day) - plus a trailing non-frost day so the last season's window is counted
    as complete (the climatology maths drops any season it has no data through to the end of)."""
    days = [
        ClimateDay(at=date(y, m, d), t_min_c=-1.0, rain_mm=0.0, gust_kmh=0.0)
        for y, m, d in first_frost_days
    ]
    last_year = max(y for y, _, _ in first_frost_days)
    days.append(ClimateDay(at=date(last_year + 1, 6, 30), t_min_c=10.0, rain_mm=0.0, gust_kmh=0.0))
    return days


def test_first_and_last_frost_takes_the_median_day_of_the_season() -> None:
    days = _winter_series([(1991, 11, 10), (1992, 11, 12), (1993, 11, 14)])
    first, last = first_and_last_frost(days)
    assert first == "11-12"
    assert last == "11-12"


def test_no_frost_data_gives_none() -> None:
    days = [ClimateDay(at=date(1991, 6, 1), t_min_c=15.0, rain_mm=0.0, gust_kmh=10.0)]
    first, last = first_and_last_frost(days)
    assert first is None
    assert last is None


def test_wettest_and_windiest_month() -> None:
    days = [
        ClimateDay(at=date(1991, 10, 1), t_min_c=5.0, rain_mm=50.0, gust_kmh=20.0),
        ClimateDay(at=date(1991, 3, 1), t_min_c=5.0, rain_mm=1.0, gust_kmh=90.0),
    ]
    assert wettest_month(days) == 10
    assert windiest_month(days) == 3


def test_oil_tank_condition_is_oil_only() -> None:
    oil = TaskContext(
        main_heating="Boiler, oil",
        main_fuel="oil",
        storm_level="low",
        river_sea_flood_level="low",
        completed_measure_ids=[],
    )
    gas = TaskContext(
        main_heating="Boiler and radiators, mains gas",
        main_fuel="mains gas",
        storm_level="low",
        river_sea_flood_level="low",
        completed_measure_ids=[],
    )
    condition = {"type": "main_fuel_is", "value": "oil"}
    assert condition_met(condition, oil) is True
    assert condition_met(condition, gas) is False


def test_before_wettest_month_resolves_to_the_prior_month() -> None:
    assert resolve_month({"type": "before_wettest_month"}, None, 1, 1) == 12
    assert resolve_month({"type": "before_wettest_month"}, None, 10, 1) == 9


def test_ics_lines_are_crlf_and_at_most_75_octets() -> None:
    tasks = [
        {
            "id": "a-very-long-task-id-that-forces-folding",
            "title": "A task title that is deliberately long enough to need folding " * 2,
            "why": "why",
            "month": 1,
            "day": 1,
        }
    ]
    body = write_ics(tasks, "abc123", datetime(2026, 1, 1))
    assert "\r\n" in body
    assert "\n\n" not in body.replace("\r\n", "")
    for line in body.split("\r\n"):
        if line:
            assert len(line.encode("utf-8")) <= 75, line


def test_fold_line_leaves_short_lines_alone() -> None:
    assert fold_line("SHORT:line") == "SHORT:line"


def test_ics_uid_is_stable_per_task_and_home() -> None:
    tasks = [{"id": "lag-outside-taps", "title": "t", "why": "w", "month": 10, "day": 20}]
    body1 = write_ics(tasks, "home123", datetime(2026, 1, 1))
    body2 = write_ics(tasks, "home123", datetime(2027, 6, 1))
    uid_line1 = next(line for line in body1.split("\r\n") if line.startswith("UID"))
    uid_line2 = next(line for line in body2.split("\r\n") if line.startswith("UID"))
    assert uid_line1 == uid_line2 == "UID:lag-outside-taps-home123@hrp"


def _mock_archive_offline(mock_http) -> None:
    mock_http.get(url__startswith=ARCHIVE_URL).mock(side_effect=httpx.ConnectError("offline"))


@pytest.mark.parametrize("ref", ["demo-flood-terrace", "demo-clay-semi", "demo-rural-cottage"])
def test_all_demo_homes_show_the_calendar_offline(client, mock_http, ref) -> None:
    _mock_archive_offline(mock_http)
    res = client.get(f"{API}/studio/homes/{ref}/care-calendar")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["months"]) == 12
    assert body["fallback_used"] is True


def test_ics_download_is_valid_calendar_and_has_no_postcode(client, mock_http) -> None:
    _mock_archive_offline(mock_http)
    res = client.get(f"{API}/studio/homes/demo-rural-cottage/care-calendar.ics")
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("text/calendar")
    assert "BEGIN:VCALENDAR" in res.text
    assert not re.search(r"\b[A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2}\b", res.text)


def test_oil_tank_task_appears_for_rural_cottage_but_not_flood_terrace(client, mock_http) -> None:
    _mock_archive_offline(mock_http)
    oil_home = client.get(f"{API}/studio/homes/demo-rural-cottage/care-calendar").json()
    gas_home = client.get(f"{API}/studio/homes/demo-flood-terrace/care-calendar").json()
    oil_ids = {t["id"] for m in oil_home["months"] for t in m["tasks"]}
    gas_ids = {t["id"] for m in gas_home["months"] for t in m["tasks"]}
    assert "oil-tank-check" in oil_ids
    assert "oil-tank-check" not in gas_ids


def test_revoked_token_feed_is_404(client, mock_http) -> None:
    _mock_archive_offline(mock_http)
    res = client.get(f"{API}/studio/ical/{uuid.uuid4().hex}.ics")
    assert res.status_code == 404, res.text


def test_subscribe_and_unsubscribe_owner_flow(user_client, mock_http) -> None:
    _mock_archive_offline(mock_http)
    household = load_fixture("city-top-flat")["household"]
    body = {
        "address": {
            "uprn": None,
            "line1": "1 Test Street",
            "postcode": "SW1A 1AA",
            "lat": 51.501009,
            "lon": -0.141588,
            "local_authority": "Westminster",
            "country": "england",
        },
        "household": household,
        "property_override": {"property_type": "flat", "source": "user"},
    }
    created = user_client.post(f"{API}/homes", json=body)
    assert created.status_code == 201, created.text
    home_id = created.json()["home_id"]
    user_client.post(f"{API}/homes/{home_id}/assess")

    sub = user_client.post(f"{API}/studio/homes/{home_id}/care-calendar/subscribe")
    assert sub.status_code == 200, sub.text
    url = sub.json()["url"]
    assert "/studio/ical/" in url

    token_path = url.split("/studio/ical/")[1]
    feed = user_client.get(f"{API}/studio/ical/{token_path}")
    assert feed.status_code == 200, feed.text

    unsub = user_client.delete(f"{API}/studio/homes/{home_id}/care-calendar/subscribe")
    assert unsub.status_code == 204, unsub.text

    feed_after = user_client.get(f"{API}/studio/ical/{token_path}")
    assert feed_after.status_code == 404, feed_after.text


def test_subscribe_rejects_demo_homes(client, mock_http) -> None:
    from tests.conftest import log_in

    log_in(client, "subscribe-demo@example.com")
    res = client.post(f"{API}/studio/homes/demo-rural-cottage/care-calendar/subscribe")
    assert res.status_code == 400, res.text
