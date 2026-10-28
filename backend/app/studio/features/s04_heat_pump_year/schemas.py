from datetime import date
from typing import Literal

from pydantic import Field

from app.schemas.base import Contract
from app.studio.common.schemas import Evidence

FlowTemp = Literal[35, 45, 55]
HtcSource = Literal["user", "estimated_from_age_band"]


class MonthlyHeatPump(Contract):
    month: int
    heat_kwh: float
    hp_cost_gbp: float
    gas_cost_gbp: float
    cop_mean: float


class DailyHeatPump(Contract):
    date: date
    t_mean_c: float
    heat_kwh: float
    cop_mean: float


class ColdestHour(Contract):
    at: str
    temp_c: float
    demand_kw: float
    hp_capacity_kw: float
    coped: bool


class AnnualHeatPump(Contract):
    heat_kwh: float
    hp_electricity_kwh: float
    gas_kwh_equivalent: float
    hp_cost_gbp: float
    gas_cost_gbp: float
    saving_gbp: float
    co2_hp_kg: float
    co2_gas_kg: float


class HeatPumpPrices(Contract):
    gas_p_per_kwh: float
    elec_p_per_kwh: float
    gas_standing_p_per_day: float
    elec_standing_p_per_day: float
    as_of: date


class HeatPumpYear(Contract):
    year: int
    htc_used_w_per_k: int
    htc_source: HtcSource
    recommended_kw: int
    scop: float
    annual: AnnualHeatPump
    monthly: list[MonthlyHeatPump] = Field(min_length=12, max_length=12)
    daily: list[DailyHeatPump]
    coldest_hour: ColdestHour
    bus_grant_gbp: int
    install_cost_low_gbp: int
    install_cost_high_gbp: int
    net_cost_low_gbp: int
    net_cost_high_gbp: int
    prices: HeatPumpPrices
    evidence: list[Evidence]
    fallback_used: bool


class HeatPumpYearRequest(Contract):
    htc_w_per_k: int | None = None
    flow_temp_c: FlowTemp = 45
    keep_gas_standing_charge: bool = False
