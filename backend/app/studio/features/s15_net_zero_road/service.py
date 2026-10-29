"""Pathway maths (docs/studio/N_20_function.md §S15 Algorithm), pure and tested."""

from app.schemas.plan import Measure
from app.services.planner import Ranked
from app.studio.features.s13_affordability_stress_test.schemas import HeatingFuel, Kwh
from app.studio.features.s15_net_zero_road.config import (
    DEFAULT_STEPS_LIMIT,
    DEFAULT_STEPS_SPACING_YEARS,
    ELECTRICITY_SAVING_MEASURE_IDS,
    FUEL_FACTOR_KG_PER_KWH,
    HEAT_PUMP_MEASURE_IDS,
    HEAT_PUMP_SCOP,
    NEAR_ZERO_THRESHOLD_KG,
    SOLAR_DEFAULT_KWP,
    SOLAR_KWH_PER_KWP,
    SOLAR_MEASURE_IDS,
    SOLAR_SELF_USE_PCT,
    YEAR_MAX,
)
from app.studio.features.s15_net_zero_road.schemas import Step, YearRow


def interpolate(series: list[tuple[int, float]], year: int) -> float:
    """Linear interpolation over a sparse, year-sorted series, clamped at the ends."""
    ordered = sorted(series)
    if year <= ordered[0][0]:
        return ordered[0][1]
    if year >= ordered[-1][0]:
        return ordered[-1][1]
    for (y0, v0), (y1, v1) in zip(ordered, ordered[1:], strict=False):
        if y0 <= year <= y1:
            if y1 == y0:
                return v0
            return v0 + (v1 - v0) * (year - y0) / (y1 - y0)
    return ordered[-1][1]


def _heating_kg(heating_fuel: HeatingFuel, heating_kwh: float) -> float:
    if heating_fuel == "electric":
        return 0.0
    return heating_kwh * FUEL_FACTOR_KG_PER_KWH.get(heating_fuel, 0.0)


def do_nothing_kg(
    kwh: Kwh, heating_fuel: HeatingFuel, year: int, grid_series: list[tuple[int, float]]
) -> float:
    elec_factor = interpolate(grid_series, year)
    return _heating_kg(heating_fuel, kwh.heating_fuel) + kwh.electricity * elec_factor


def with_plan_kg(
    kwh: Kwh,
    heating_fuel: HeatingFuel,
    year: int,
    grid_series: list[tuple[int, float]],
    applied: list[Measure],
    baseline_grid_factor: float,
) -> float:
    elec_factor = interpolate(grid_series, year)
    heating_kwh = float(kwh.heating_fuel)
    electricity_kwh = float(kwh.electricity)

    if heating_fuel != "electric" and any(m.id in HEAT_PUMP_MEASURE_IDS for m in applied):
        electricity_kwh += heating_kwh / HEAT_PUMP_SCOP
        heating_kwh = 0.0

    if any(m.id in SOLAR_MEASURE_IDS for m in applied):
        generated = SOLAR_KWH_PER_KWP * SOLAR_DEFAULT_KWP * SOLAR_SELF_USE_PCT
        electricity_kwh = max(0.0, electricity_kwh - generated)

    flat_reduction_kg = 0.0
    for m in applied:
        if m.id in HEAT_PUMP_MEASURE_IDS or m.id in SOLAR_MEASURE_IDS:
            continue
        if m.id in ELECTRICITY_SAVING_MEASURE_IDS:
            ratio = (elec_factor / baseline_grid_factor) if baseline_grid_factor else 1.0
            flat_reduction_kg += m.co2_saved_kg_per_year * ratio
        else:
            flat_reduction_kg += m.co2_saved_kg_per_year

    total = (
        _heating_kg(heating_fuel, heating_kwh) + electricity_kwh * elec_factor - flat_reduction_kg
    )
    return max(0.0, total)


def pathway_kg(
    base_year_do_nothing_kg: float, year: int, ccc_series: list[tuple[int, float]]
) -> float:
    return base_year_do_nothing_kg * interpolate(ccc_series, year) / 100


def near_zero_year(years: list[YearRow]) -> int | None:
    return next((r.year for r in years if r.co2_kg_with_plan < NEAR_ZERO_THRESHOLD_KG), None)


def cumulative_saved_kg(years: list[YearRow]) -> int:
    return sum(r.co2_kg_do_nothing - r.co2_kg_with_plan for r in years)


def default_steps_for(ranked: list[Ranked], start_year: int) -> list[Step]:
    top = ranked[:DEFAULT_STEPS_LIMIT]
    return [
        Step(
            measure_id=r.measure.id,
            year=min(YEAR_MAX, start_year + 1 + DEFAULT_STEPS_SPACING_YEARS * i),
        )
        for i, r in enumerate(top)
    ]
