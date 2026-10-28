from datetime import date
from typing import Literal

from app.schemas.base import Contract
from app.studio.common.schemas import Evidence

Fuel = Literal["gas", "electric_heat_pump", "electric_direct"]
Unit = Literal["kwh", "m3"]
Rating = Literal["excellent", "good", "average", "poor"]


class ScatterPoint(Contract):
    t_mean_c: float
    kwh: float


class Fingerprint(Contract):
    days_used: int
    period_start: date
    period_end: date
    base_temp_c: float
    baseload_kwh_per_day: float
    slope_kwh_per_degree_day: float
    htc_w_per_k: int
    htc_ci_low: int
    htc_ci_high: int
    hlp_w_per_m2k: float | None
    r2: float
    rating: Rating
    normalised_annual_heating_kwh: int
    scatter: list[ScatterPoint]
    fit: list[ScatterPoint]
    evidence: list[Evidence]
    fallback_used: bool
