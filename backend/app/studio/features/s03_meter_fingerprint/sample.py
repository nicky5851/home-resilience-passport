"""A synthetic sample CSV for demo homes — a known HTC plus noise, seeded so the sample is
stable (docs/studio/N_20_function.md §S03 build step 4)."""

import csv
import io
import random
from datetime import date, timedelta

SAMPLE_SEED = 20261028
SAMPLE_DAYS = 120
SAMPLE_START = date(2025, 11, 1)
SAMPLE_BASE_TEMP_C = 15.5
SAMPLE_BASELOAD_KWH = 6.0
SAMPLE_SLOPE_KWH_PER_DD = 7.5  # ~ HTC 265 W/K for a gas boiler at eta 0.85


def _synthetic_temp(day_index: int) -> float:
    """A smooth seasonal curve through a UK winter, +/- daily noise (seeded)."""
    rng = random.Random(SAMPLE_SEED + day_index)
    import math

    base = 8.0 - 6.0 * math.cos(2 * math.pi * day_index / 365)
    return round(base + rng.uniform(-2.5, 2.5), 1)


def generate_sample_rows() -> list[tuple[str, float]]:
    rows = []
    for i in range(SAMPLE_DAYS):
        day = SAMPLE_START + timedelta(days=i)
        t = _synthetic_temp(i)
        rng = random.Random(SAMPLE_SEED + 1000 + i)
        kwh = SAMPLE_BASELOAD_KWH + SAMPLE_SLOPE_KWH_PER_DD * max(0.0, SAMPLE_BASE_TEMP_C - t)
        kwh += rng.uniform(-1.0, 1.0)
        rows.append((day.isoformat(), round(max(0.0, kwh), 2)))
    return rows


def sample_csv_text() -> str:
    buf = io.StringIO()
    buf.write("# SAMPLE DATA - synthetic, for trying Meter Fingerprint without a real export\n")
    writer = csv.writer(buf)
    writer.writerow(["date", "consumption_kwh"])
    for day_iso, kwh in generate_sample_rows():
        writer.writerow([day_iso, kwh])
    return buf.getvalue()


def sample_temps() -> dict[date, float]:
    return {SAMPLE_START + timedelta(days=i): _synthetic_temp(i) for i in range(SAMPLE_DAYS)}
