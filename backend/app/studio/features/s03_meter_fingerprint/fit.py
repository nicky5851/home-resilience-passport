"""The change-point regression and HTC math (docs/studio/N_20_function.md §S03 steps 3-7).
Pure, deterministic (the bootstrap is seeded), and fast — no network, easy to unit-test."""

import random
from dataclasses import dataclass

from app.studio.features.s03_meter_fingerprint.config import (
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    CHANGE_POINT_MAX_C,
    CHANGE_POINT_MIN_C,
    CHANGE_POINT_STEP_C,
    CI_HIGH_PERCENTILE,
    CI_LOW_PERCENTILE,
    EFFICIENCY,
    RATING_BANDS,
    RATING_POOR,
)


@dataclass
class Point:
    t_mean_c: float
    kwh: float


@dataclass
class FitResult:
    base_temp_c: float
    baseload_kwh_per_day: float
    slope_kwh_per_degree_day: float
    r2: float


def _heating_degree(t: float, base_temp: float) -> float:
    return max(0.0, base_temp - t)


def _least_squares(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """`y = a + b*x`; returns (a, b, sse)."""
    n = len(xs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x == 0:
        a = mean_y
        sse = sum((y - a) ** 2 for y in ys)
        return a, 0.0, sse
    cov_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    b = cov_xy / var_x
    a = mean_y - b * mean_x
    sse = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys, strict=True))
    return a, b, sse


def fit_change_point(points: list[Point]) -> FitResult:
    """Try every base temperature 12.0-18.0 step 0.5; keep the one with lowest sum of squared
    error (docs/studio/N_20_function.md §S03 step 3)."""
    best: tuple[float, float, float, float] | None = None  # (base, a, b, sse)
    tb = CHANGE_POINT_MIN_C
    while tb <= CHANGE_POINT_MAX_C + 1e-9:
        xs = [_heating_degree(p.t_mean_c, tb) for p in points]
        ys = [p.kwh for p in points]
        a, b, sse = _least_squares(xs, ys)
        if best is None or sse < best[3]:
            best = (tb, a, b, sse)
        tb = round(tb + CHANGE_POINT_STEP_C, 4)

    base_temp, a, b, sse = best
    ys = [p.kwh for p in points]
    mean_y = sum(ys) / len(ys)
    sst = sum((y - mean_y) ** 2 for y in ys) or 1.0
    r2 = max(0.0, 1 - sse / sst)
    return FitResult(
        base_temp_c=base_temp,
        baseload_kwh_per_day=round(a, 3),
        slope_kwh_per_degree_day=round(b, 4),
        r2=round(r2, 3),
    )


def htc_w_per_k(slope_kwh_per_degree_day: float, fuel: str) -> float:
    """Watts per kelvin from kWh/degree-day, correcting for system efficiency (config §EFFICIENCY).

    1 kWh/degree-day = 1000 Wh / 24 h per 1 K = 1000/24 W/K of *metered fuel*; dividing by
    efficiency converts that into W/K of *delivered heat loss*.
    """
    eta = EFFICIENCY[fuel]
    return slope_kwh_per_degree_day * 1000 / 24 * eta


def bootstrap_ci(
    points: list[Point], fuel: str, resamples: int = BOOTSTRAP_RESAMPLES
) -> tuple[int, int]:
    rng = random.Random(BOOTSTRAP_SEED)
    n = len(points)
    htcs = []
    for _ in range(resamples):
        sample = [points[rng.randrange(n)] for _ in range(n)]
        fit = fit_change_point(sample)
        htcs.append(htc_w_per_k(fit.slope_kwh_per_degree_day, fuel))
    htcs.sort()
    lo_idx = max(0, min(n - 1, round(CI_LOW_PERCENTILE / 100 * len(htcs))))
    hi_idx = max(0, min(len(htcs) - 1, round(CI_HIGH_PERCENTILE / 100 * len(htcs))))
    return round(htcs[lo_idx]), round(htcs[hi_idx])


def hlp_rating(hlp: float | None) -> str:
    if hlp is None:
        return RATING_POOR
    for upper, label in RATING_BANDS:
        if hlp < upper:
            return label
    return RATING_POOR


def annual_heating_degree_days(base_temp_c: float) -> float:
    """HDD(base_temp) from the UK 1991-2020 monthly-mean climatology (config.py)."""
    from app.studio.features.s03_meter_fingerprint.config import (
        DAYS_PER_MONTH,
        UK_MONTHLY_MEAN_TEMP_C,
    )

    return sum(
        days * max(0.0, base_temp_c - mean_t)
        for days, mean_t in zip(DAYS_PER_MONTH, UK_MONTHLY_MEAN_TEMP_C, strict=True)
    )


def normalised_annual_heating_kwh(slope_kwh_per_degree_day: float, base_temp_c: float) -> int:
    """`slope x HDD(base_temp)`, weather-normalised to a typical UK year."""
    return round(slope_kwh_per_degree_day * annual_heating_degree_days(base_temp_c))
