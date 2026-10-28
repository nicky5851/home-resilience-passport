"""Pure hour-by-hour heat-pump simulation (docs/studio/N_20_function.md §S04 algorithm 1-5)."""

from dataclasses import dataclass
from datetime import datetime

from app.studio.features.s04_heat_pump_year.config import (
    COP_COEFFICIENT,
    COP_MAX,
    COP_MIN,
    DAY_END_HOUR,
    DAY_START_HOUR,
    DEFROST_HIGH_C,
    DEFROST_LOW_C,
    DEFROST_PENALTY,
    DESIGN_INDOOR_C,
    DESIGN_OUTDOOR_C,
    INTERNAL_GAIN_K,
    SIZE_STEPS_KW,
    T_SET_DAY_C,
    T_SET_NIGHT_C,
)


@dataclass
class HourResult:
    at: datetime
    t_out_c: float
    demand_kw: float
    cop: float
    electricity_kwh: float


def t_set_c(hour: int) -> float:
    return T_SET_DAY_C if DAY_START_HOUR <= hour < DAY_END_HOUR else T_SET_NIGHT_C


def demand_kw(htc_w_per_k: float, t_out_c: float, hour: int) -> float:
    deficit = max(0.0, t_set_c(hour) - t_out_c - INTERNAL_GAIN_K)
    return htc_w_per_k * deficit / 1000


def cop_for(t_out_c: float, flow_temp_c: int) -> float:
    t_flow_k = flow_temp_c + 273.15
    t_out_k = t_out_c + 273.15
    cop = COP_COEFFICIENT * t_flow_k / (t_flow_k - t_out_k) if t_flow_k != t_out_k else COP_MAX
    cop = max(COP_MIN, min(COP_MAX, cop))
    if DEFROST_LOW_C <= t_out_c <= DEFROST_HIGH_C:
        cop *= 1 - DEFROST_PENALTY
    return cop


def recommended_kw(htc_w_per_k: float) -> int:
    needed = htc_w_per_k * (DESIGN_INDOOR_C - DESIGN_OUTDOOR_C) / 1000
    for step in SIZE_STEPS_KW:
        if step >= needed:
            return step
    return SIZE_STEPS_KW[-1]


def simulate_year(
    htc_w_per_k: float, flow_temp_c: int, hourly: list[tuple[datetime, float]]
) -> list[HourResult]:
    results = []
    for at, t_out in hourly:
        demand = demand_kw(htc_w_per_k, t_out, at.hour)
        cop = cop_for(t_out, flow_temp_c)
        results.append(
            HourResult(
                at=at,
                t_out_c=t_out,
                demand_kw=demand,
                cop=cop,
                electricity_kwh=demand / cop if cop > 0 else 0.0,
            )
        )
    return results
