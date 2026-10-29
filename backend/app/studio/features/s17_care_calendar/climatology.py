"""Climatology maths (docs/studio/N_20_function.md §S17 Algorithm 1), pure and tested."""

import statistics
from dataclasses import dataclass
from datetime import date, timedelta

REFERENCE_YEAR = 2001  # a non-leap year, used only to format a median offset back to "MM-DD"


@dataclass
class ClimateDay:
    at: date
    t_min_c: float | None
    rain_mm: float | None
    gust_kmh: float | None


def _season_offsets(days: list[ClimateDay]) -> tuple[list[int], list[int]]:
    """For each winter season (1 Aug of year Y to 30 Jun of year Y+1), the day offset from
    1 Aug of the first and last day with a min temperature at or below 0°C."""
    by_date = {d.at: d.t_min_c for d in days}
    if not by_date:
        return [], []
    max_date = max(by_date)
    years = sorted({d.year for d in by_date})

    first_offsets: list[int] = []
    last_offsets: list[int] = []
    for year in years:
        season_start = date(year, 8, 1)
        season_end = date(year + 1, 6, 30)
        if season_end > max_date:
            continue
        frost_dates = [
            d
            for d in by_date
            if season_start <= d <= season_end and (by_date[d] or 0) <= 0 and by_date[d] is not None
        ]
        if not frost_dates:
            continue
        frost_dates.sort()
        first_offsets.append((frost_dates[0] - season_start).days)
        last_offsets.append((frost_dates[-1] - season_start).days)
    return first_offsets, last_offsets


def _offset_to_mmdd(offset: int) -> str:
    return (date(REFERENCE_YEAR, 8, 1) + timedelta(days=offset)).strftime("%m-%d")


def first_and_last_frost(days: list[ClimateDay]) -> tuple[str | None, str | None]:
    first_offsets, last_offsets = _season_offsets(days)
    first = _offset_to_mmdd(round(statistics.median(first_offsets))) if first_offsets else None
    last = _offset_to_mmdd(round(statistics.median(last_offsets))) if last_offsets else None
    return first, last


def wettest_month(days: list[ClimateDay]) -> int:
    by_month: dict[int, list[float]] = {m: [] for m in range(1, 13)}
    totals: dict[tuple[int, int], float] = {}
    for d in days:
        if d.rain_mm is None:
            continue
        totals[(d.at.year, d.at.month)] = totals.get((d.at.year, d.at.month), 0.0) + d.rain_mm
    for (_, month), total in totals.items():
        by_month[month].append(total)
    means = {m: statistics.mean(v) for m, v in by_month.items() if v}
    return max(means, key=lambda m: means[m]) if means else 1


def windiest_month(days: list[ClimateDay]) -> int:
    by_month: dict[int, list[float]] = {m: [] for m in range(1, 13)}
    for d in days:
        if d.gust_kmh is not None:
            by_month[d.at.month].append(d.gust_kmh)
    means = {m: statistics.mean(v) for m, v in by_month.items() if v}
    return max(means, key=lambda m: means[m]) if means else 1
