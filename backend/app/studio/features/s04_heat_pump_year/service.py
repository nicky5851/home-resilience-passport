from collections import defaultdict
from datetime import date

from app.schemas.property import PropertyFacts
from app.studio.features.s04_heat_pump_year.config import (
    BOILER_EFFICIENCY,
    CO2_KG_PER_KWH_ELEC,
    CO2_KG_PER_KWH_GAS,
    ELEC_P_PER_KWH,
    ELEC_STANDING_P_PER_DAY,
    FORM_FACTOR,
    FORM_FACTOR_DEFAULT,
    GAS_P_PER_KWH,
    GAS_STANDING_P_PER_DAY,
    HLP_BY_AGE_BAND,
    HLP_DEFAULT,
)
from app.studio.features.s04_heat_pump_year.schemas import (
    AnnualHeatPump,
    ColdestHour,
    DailyHeatPump,
    HeatPumpPrices,
    MonthlyHeatPump,
)
from app.studio.features.s04_heat_pump_year.sim import HourResult, demand_kw


def form_factor_for(prop: PropertyFacts) -> float:
    built_form = (prop.built_form or "").lower()
    if "mid" in built_form and "terrace" in built_form:
        return FORM_FACTOR["mid-terrace"]
    if "end" in built_form and "terrace" in built_form:
        return FORM_FACTOR["end-terrace"]
    if "semi" in built_form:
        return FORM_FACTOR["semi-detached"]
    if "detached" in built_form:
        return FORM_FACTOR["detached"]
    if prop.property_type == "bungalow":
        return FORM_FACTOR["bungalow"]
    if prop.property_type == "flat":
        return FORM_FACTOR["flat"]
    if prop.property_type == "terraced":
        return FORM_FACTOR["mid-terrace"]
    if prop.property_type == "detached":
        return FORM_FACTOR["detached"]
    return FORM_FACTOR_DEFAULT


def estimate_htc_w_per_k(prop: PropertyFacts) -> int:
    hlp = HLP_BY_AGE_BAND.get(prop.construction_age_band or "", HLP_DEFAULT)
    area = prop.floor_area_m2 or 90.0
    return round(hlp * area * form_factor_for(prop))


def build_year(
    hourly_results: list[HourResult],
    htc_w_per_k: float,
    htc_source: str,
    recommended: int,
    gas_standing_kept: bool,
) -> dict:
    daily_by_date: dict = defaultdict(lambda: {"heat_kwh": 0.0, "temps": [], "cops": []})
    monthly_by_month: dict = defaultdict(lambda: {"heat_kwh": 0.0, "cops": []})
    total_heat = total_elec = 0.0
    coldest: HourResult | None = None

    for r in hourly_results:
        day = r.at.date()
        bucket = daily_by_date[day]
        bucket["heat_kwh"] += r.demand_kw
        bucket["temps"].append(r.t_out_c)
        bucket["cops"].append(r.cop)

        mbucket = monthly_by_month[r.at.month]
        mbucket["heat_kwh"] += r.demand_kw
        mbucket["cops"].append(r.cop)

        total_heat += r.demand_kw
        total_elec += r.electricity_kwh

        if coldest is None or r.t_out_c < coldest.t_out_c:
            coldest = r

    daily = [
        DailyHeatPump(
            date=d,
            t_mean_c=round(sum(b["temps"]) / len(b["temps"]), 1),
            heat_kwh=round(b["heat_kwh"], 2),
            cop_mean=round(sum(b["cops"]) / len(b["cops"]), 2),
        )
        for d, b in sorted(daily_by_date.items())
    ]

    gas_kwh_equivalent = total_heat / BOILER_EFFICIENCY
    monthly = [
        MonthlyHeatPump(
            month=m,
            heat_kwh=round(b["heat_kwh"], 1),
            hp_cost_gbp=round(_month_elec_kwh(hourly_results, m) * ELEC_P_PER_KWH / 100, 2),
            gas_cost_gbp=round((b["heat_kwh"] / BOILER_EFFICIENCY) * GAS_P_PER_KWH / 100, 2),
            cop_mean=round(sum(b["cops"]) / len(b["cops"]), 2),
        )
        for m, b in sorted(monthly_by_month.items())
    ]

    hp_cost_gbp = total_elec * ELEC_P_PER_KWH / 100 + 365 * ELEC_STANDING_P_PER_DAY / 100
    gas_cost_gbp = gas_kwh_equivalent * GAS_P_PER_KWH / 100
    if not gas_standing_kept:
        gas_cost_gbp_with_standing = gas_cost_gbp
    else:
        gas_cost_gbp_with_standing = gas_cost_gbp + 365 * GAS_STANDING_P_PER_DAY / 100

    assert coldest is not None
    coldest_demand = demand_kw(htc_w_per_k, coldest.t_out_c, coldest.at.hour)
    coldest_hour = ColdestHour(
        at=coldest.at.isoformat(),
        temp_c=round(coldest.t_out_c, 1),
        demand_kw=round(coldest_demand, 2),
        hp_capacity_kw=recommended,
        coped=coldest_demand <= recommended,
    )

    scop = total_heat / total_elec if total_elec > 0 else 0.0

    annual = AnnualHeatPump(
        heat_kwh=round(total_heat, 0),
        hp_electricity_kwh=round(total_elec, 0),
        gas_kwh_equivalent=round(gas_kwh_equivalent, 0),
        hp_cost_gbp=round(hp_cost_gbp, 0),
        gas_cost_gbp=round(gas_cost_gbp_with_standing, 0),
        saving_gbp=round(gas_cost_gbp_with_standing - hp_cost_gbp, 0),
        co2_hp_kg=round(total_elec * CO2_KG_PER_KWH_ELEC, 0),
        co2_gas_kg=round(gas_kwh_equivalent * CO2_KG_PER_KWH_GAS, 0),
    )

    return {
        "scop": round(scop, 2),
        "annual": annual,
        "monthly": monthly,
        "daily": daily,
        "coldest_hour": coldest_hour,
        "prices": HeatPumpPrices(
            gas_p_per_kwh=GAS_P_PER_KWH,
            elec_p_per_kwh=ELEC_P_PER_KWH,
            gas_standing_p_per_day=GAS_STANDING_P_PER_DAY,
            elec_standing_p_per_day=ELEC_STANDING_P_PER_DAY,
            as_of=date.today(),
        ),
    }


def _month_elec_kwh(hourly_results: list[HourResult], month: int) -> float:
    return sum(r.electricity_kwh for r in hourly_results if r.at.month == month)
