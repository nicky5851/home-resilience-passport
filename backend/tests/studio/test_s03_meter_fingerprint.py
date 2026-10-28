"""S03: CSV parsing edge cases, the change-point fit recovering a known HTC, and the route
against demo homes (sample data, never the network)."""

import math
import random
from datetime import date, timedelta

import pytest

from app.studio.features.s03_meter_fingerprint.config import M3_TO_KWH
from app.studio.features.s03_meter_fingerprint.fit import (
    Point,
    fit_change_point,
    hlp_rating,
    htc_w_per_k,
)
from app.studio.features.s03_meter_fingerprint.parser import UnreadableFile, parse_consumption_csv
from app.studio.features.s03_meter_fingerprint.service import (
    build_fingerprint,
    count_winter_days,
)

API = "/api/v1"


def _synthetic_points(true_htc_w_per_k: float, eta: float = 0.85, n: int = 150) -> list[Point]:
    rng = random.Random(42)
    slope = true_htc_w_per_k / (1000 / 24 * eta)
    points = []
    for i in range(n):
        t = 10.0 - 8.0 * math.cos(2 * math.pi * i / 365) + rng.uniform(-3, 3)
        base = 15.0
        kwh = 5.0 + slope * max(0.0, base - t) + rng.uniform(-0.5, 0.5)
        points.append(Point(t_mean_c=round(t, 1), kwh=max(0.0, kwh)))
    return points


def test_fit_recovers_a_known_htc_within_ten_percent() -> None:
    points = _synthetic_points(200.0)
    fit = fit_change_point(points)
    htc = htc_w_per_k(fit.slope_kwh_per_degree_day, "gas")
    assert 190 <= htc <= 210


def test_hlp_rating_bands() -> None:
    assert hlp_rating(0.8) == "excellent"
    assert hlp_rating(1.5) == "good"
    assert hlp_rating(2.5) == "average"
    assert hlp_rating(4.0) == "poor"
    assert hlp_rating(None) == "poor"


def test_m3_to_kwh_conversion_matches_gov_uk_formula() -> None:
    assert M3_TO_KWH == pytest.approx(1.02264 * 39.5 / 3.6, rel=1e-9)
    csv_bytes = b"date,m3\n2026-01-01,10\n2026-01-02,12\n"
    readings = parse_consumption_csv(csv_bytes, "m3")
    assert readings[0].kwh == pytest.approx(10 * M3_TO_KWH)


def test_parses_semicolon_delimited_file_with_a_bom() -> None:
    csv_bytes = "﻿date;consumption_kwh\n2026-01-01;12,5\n2026-01-02;13,0\n".encode()
    readings = parse_consumption_csv(csv_bytes, "kwh")
    assert len(readings) == 2
    assert readings[0].day == date(2026, 1, 1)


def test_half_hourly_readings_sum_to_one_day() -> None:
    csv_bytes = (
        b"timestamp,kwh\n"
        b"2026-01-01T00:00:00,0.5\n2026-01-01T00:30:00,0.5\n2026-01-01T01:00:00,0.4\n"
        b"2026-01-02T00:00:00,0.6\n"
    )
    readings = parse_consumption_csv(csv_bytes, "kwh")
    assert len(readings) == 2
    assert readings[0].day == date(2026, 1, 1)
    assert readings[0].kwh == pytest.approx(1.4)


def test_a_png_renamed_to_csv_is_unreadable() -> None:
    png_bytes = b"\x89PNG\r\n\x1a\n" + bytes(range(200))
    with pytest.raises(UnreadableFile):
        parse_consumption_csv(png_bytes, "kwh")


def test_fewer_than_sixty_winter_days_is_rejected() -> None:
    import app.studio.features.s03_meter_fingerprint.parser as parser_mod
    from app.studio.features.s03_meter_fingerprint.service import NotEnoughWinterData

    points = [Point(t_mean_c=15.0, kwh=5.0) for _ in range(10)]
    assert count_winter_days(points) == 0
    readings_stub = [
        parser_mod.DailyReading(day=date(2026, 1, 1) + timedelta(days=i), kwh=5.0)
        for i in range(10)
    ]
    with pytest.raises(NotEnoughWinterData):
        build_fingerprint(readings_stub, points, "gas", 80.0)


def test_route_sample_csv_download(client) -> None:
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/meter-fingerprint/sample.csv")
    assert res.status_code == 200, res.text
    assert "SAMPLE DATA" in res.text


def test_route_sample_fingerprint(client) -> None:
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/meter-fingerprint/sample")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["htc_w_per_k"] > 0
    assert body["rating"] in ("excellent", "good", "average", "poor")


def test_route_upload_too_large_file_is_rejected(client) -> None:
    big = b"date,kwh\n" + b"2026-01-01,1\n" * 300_000
    assert len(big) > 2 * 1024 * 1024
    res = client.post(
        f"{API}/studio/homes/demo-flood-terrace/meter-fingerprint",
        files={"file": ("big.csv", big, "text/csv")},
        data={"fuel": "gas", "unit": "kwh"},
    )
    assert res.status_code == 413, res.text
    assert res.json()["code"] == "file_too_large"


def test_route_upload_unreadable_file_is_rejected(client) -> None:
    res = client.post(
        f"{API}/studio/homes/demo-flood-terrace/meter-fingerprint",
        files={"file": ("photo.csv", b"\x89PNG\r\n\x1a\n" + bytes(range(50)), "text/csv")},
        data={"fuel": "gas", "unit": "kwh"},
    )
    assert res.status_code == 415, res.text
    assert res.json()["code"] == "unsupported_file"
