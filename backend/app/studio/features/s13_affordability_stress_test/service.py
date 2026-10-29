"""Scenario maths (docs/studio/N_20_function.md §S13 Algorithm), pure and tested."""

from app.schemas.plan import Measure
from app.schemas.property import PropertyFacts
from app.studio.features.s13_affordability_stress_test.config import (
    AFFORDABILITY_PCT_THRESHOLD,
    AGE_BAND_KWH_PER_M2,
    DEFAULT_FLOOR_AREA_M2,
    DEFAULT_HEATING_FUEL,
    DEFAULT_KWH_PER_M2,
    FUEL_FOR_MAIN_FUEL,
    GAS_HEATING_ELECTRICITY_SHARE,
    LPG_P_PER_KWH,
    OIL_P_PER_KWH,
    SHOCK_30_MULTIPLIER,
)
from app.studio.features.s13_affordability_stress_test.schemas import HeatingFuel, Kwh, Scenario


def heating_fuel_for(main_fuel: str | None) -> HeatingFuel:
    if main_fuel in FUEL_FOR_MAIN_FUEL:
        return FUEL_FOR_MAIN_FUEL[main_fuel]  # type: ignore[return-value]
    return "other" if main_fuel else DEFAULT_HEATING_FUEL  # type: ignore[return-value]


def estimate_kwh(prop: PropertyFacts, heating_fuel: HeatingFuel) -> Kwh:
    floor_area = prop.floor_area_m2 or DEFAULT_FLOOR_AREA_M2
    per_m2 = AGE_BAND_KWH_PER_M2.get(prop.construction_age_band or "", DEFAULT_KWH_PER_M2)
    total_kwh = per_m2 * floor_area

    if heating_fuel == "electric":
        return Kwh(heating_fuel=0, electricity=round(total_kwh))

    electricity = round(total_kwh * GAS_HEATING_ELECTRICITY_SHARE)
    return Kwh(heating_fuel=round(total_kwh - electricity), electricity=electricity)


def _unit_rate_p(heating_fuel: HeatingFuel, cap: dict[str, float]) -> float:
    if heating_fuel == "oil":
        return OIL_P_PER_KWH
    if heating_fuel == "lpg":
        return LPG_P_PER_KWH
    return cap["gas_p_per_kwh"]


def annual_cost_gbp(kwh: Kwh, heating_fuel: HeatingFuel, cap: dict[str, float]) -> float:
    heating_rate = _unit_rate_p(heating_fuel, cap)
    heating_cost_p = kwh.heating_fuel * heating_rate
    electricity_cost_p = kwh.electricity * cap["elec_p_per_kwh"]

    standing_p = 365 * cap["elec_standing_p_per_day"]
    if heating_fuel == "gas":
        standing_p += 365 * cap["gas_standing_p_per_day"]

    return (heating_cost_p + electricity_cost_p + standing_p) / 100


def shock_30_cap(today_cap: dict[str, float]) -> dict[str, float]:
    return {k: v * SHOCK_30_MULTIPLIER for k, v in today_cap.items()}


def after_plan_cost_gbp(
    cost_gbp: float, measures: list[Measure], price_ratio_to_today: float, standing_floor_gbp: float
) -> float:
    savings = sum(m.annual_bill_saving_gbp for m in measures) * price_ratio_to_today
    return max(standing_floor_gbp, cost_gbp - savings)


def pct_income(cost_gbp: float, income_midpoint_gbp: int) -> float:
    return round(100 * cost_gbp / income_midpoint_gbp, 1)


def build_scenario(
    scenario_id: str,
    label: str,
    cost_gbp: float,
    cost_after_gbp: float | None,
    income_midpoint_gbp: int | None,
) -> Scenario:
    pct = pct_income(cost_gbp, income_midpoint_gbp) if income_midpoint_gbp else None
    pct_after = (
        pct_income(cost_after_gbp, income_midpoint_gbp)
        if income_midpoint_gbp and cost_after_gbp is not None
        else None
    )
    return Scenario(
        id=scenario_id,
        label=label,
        annual_cost_gbp=round(cost_gbp),
        annual_cost_after_gbp=round(cost_after_gbp) if cost_after_gbp is not None else None,
        pct_income=pct,
        pct_income_after=pct_after,
        above_10pct=None if pct is None else pct > AFFORDABILITY_PCT_THRESHOLD,
        above_10pct_after=None if pct_after is None else pct_after > AFFORDABILITY_PCT_THRESHOLD,
    )
