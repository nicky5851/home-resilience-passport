"""Glue between the parsed CSV, ERA5 weather and the fit — the piece the router calls."""

from datetime import date

from app.studio.features.s03_meter_fingerprint.config import MIN_WINTER_DAYS, WINTER_TEMP_C
from app.studio.features.s03_meter_fingerprint.fit import (
    FitResult,
    Point,
    bootstrap_ci,
    fit_change_point,
    hlp_rating,
    htc_w_per_k,
    normalised_annual_heating_kwh,
)
from app.studio.features.s03_meter_fingerprint.parser import DailyReading
from app.studio.features.s03_meter_fingerprint.schemas import Fingerprint, ScatterPoint


class NotEnoughWinterData(Exception):
    pass


def join_weather(readings: list[DailyReading], temps: dict[date, float]) -> list[Point]:
    return [Point(t_mean_c=temps[r.day], kwh=r.kwh) for r in readings if r.day in temps]


def count_winter_days(points: list[Point]) -> int:
    return sum(1 for p in points if p.t_mean_c < WINTER_TEMP_C)


def build_fingerprint(
    readings: list[DailyReading], points: list[Point], fuel: str, floor_area_m2: float | None
) -> Fingerprint:
    if count_winter_days(points) < MIN_WINTER_DAYS:
        raise NotEnoughWinterData

    fit: FitResult = fit_change_point(points)
    htc = htc_w_per_k(fit.slope_kwh_per_degree_day, fuel)
    ci_low, ci_high = bootstrap_ci(points, fuel)
    hlp = htc / floor_area_m2 if floor_area_m2 else None

    return Fingerprint(
        days_used=len(readings),
        period_start=readings[0].day,
        period_end=readings[-1].day,
        base_temp_c=fit.base_temp_c,
        baseload_kwh_per_day=fit.baseload_kwh_per_day,
        slope_kwh_per_degree_day=fit.slope_kwh_per_degree_day,
        htc_w_per_k=round(htc),
        htc_ci_low=ci_low,
        htc_ci_high=ci_high,
        hlp_w_per_m2k=round(hlp, 2) if hlp is not None else None,
        r2=fit.r2,
        rating=hlp_rating(hlp),
        normalised_annual_heating_kwh=normalised_annual_heating_kwh(
            fit.slope_kwh_per_degree_day, fit.base_temp_c
        ),
        scatter=[ScatterPoint(t_mean_c=round(p.t_mean_c, 1), kwh=round(p.kwh, 2)) for p in points][
            :400
        ],
        fit=_fit_line(fit, points),
        evidence=[],
        fallback_used=False,
    )


def _fit_line(fit: FitResult, points: list[Point]) -> list[ScatterPoint]:
    temps = sorted({round(p.t_mean_c, 1) for p in points})
    if not temps:
        return []
    lo, hi = temps[0], temps[-1]
    xs = [lo + (hi - lo) * i / 20 for i in range(21)]
    return [
        ScatterPoint(
            t_mean_c=round(t, 1),
            kwh=round(
                fit.baseload_kwh_per_day
                + fit.slope_kwh_per_degree_day * max(0.0, fit.base_temp_c - t),
                2,
            ),
        )
        for t in xs
    ]
