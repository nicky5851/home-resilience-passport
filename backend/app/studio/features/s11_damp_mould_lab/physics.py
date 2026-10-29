"""Condensation physics (docs/studio/N_20_function.md §S11 Algorithm steps 2-6), pure and
tested. BS EN ISO 13788 surface-humidity criterion; Magnus formula for saturation vapour
pressure."""

import math

from app.studio.features.s11_damp_mould_lab.config import (
    CORNER_FRSI_PENALTY,
    DELTA_P_AT_ZERO_C,
    RSI_WALL,
)


def p_sat(temp_c: float) -> float:
    """Magnus formula, saturation vapour pressure in Pa."""
    return 611.2 * math.exp((17.62 * temp_c) / (243.12 + temp_c))


def f_rsi(u_value: float, rsi: float = RSI_WALL) -> float:
    return 1 - u_value * rsi


def corner_f_rsi(wall_f_rsi: float) -> float:
    return wall_f_rsi - CORNER_FRSI_PENALTY


def surface_temp_c(theta_e: float, theta_i: float, frsi: float) -> float:
    return theta_e + frsi * (theta_i - theta_e)


def delta_p_pa(moisture_class: int, theta_e: float) -> float:
    """Excess vapour pressure (Pa) for this moisture class, falling linearly to 0 at 20C."""
    base = DELTA_P_AT_ZERO_C[moisture_class]
    if theta_e >= 20:
        return 0.0
    if theta_e <= 0:
        return base
    return base * (1 - theta_e / 20)


def surface_rh(
    theta_e: float, rh_e: float, theta_i: float, frsi: float, moisture_class: int
) -> float:
    """`rh_e` is the hour's actual external relative humidity (0-1), from ERA5."""
    theta_si = surface_temp_c(theta_e, theta_i, frsi)
    p_e = rh_e * p_sat(theta_e)
    p_i = p_e + delta_p_pa(moisture_class, theta_e)
    return p_i / p_sat(theta_si)


def moisture_class_for(
    occupants: int,
    dries_clothes_indoors: bool,
    kitchen_extractor: bool,
    bathroom_extractor: bool,
    trickle_vents: bool,
) -> int:
    cls = 2
    if occupants >= 4 or dries_clothes_indoors:
        cls += 1
    if not (bathroom_extractor and kitchen_extractor):
        cls += 1
    if kitchen_extractor and bathroom_extractor and trickle_vents:
        cls -= 1
    return max(1, min(4, cls))


def level_for(risk_pct: float, low_max: float, medium_max: float) -> str:
    if risk_pct < low_max:
        return "low"
    if risk_pct <= medium_max:
        return "medium"
    return "high"
