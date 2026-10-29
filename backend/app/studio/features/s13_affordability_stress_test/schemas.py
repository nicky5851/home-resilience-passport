from typing import Literal

from app.schemas.base import Contract
from app.studio.common.schemas import Evidence

ScenarioId = Literal["today", "peak_2022", "shock_30", "pre_crisis_2021"]
HeatingFuel = Literal["gas", "electric", "oil", "lpg", "other"]


class Kwh(Contract):
    heating_fuel: int
    electricity: int


class Scenario(Contract):
    id: ScenarioId
    label: str
    annual_cost_gbp: int
    annual_cost_after_gbp: int | None
    pct_income: float | None
    pct_income_after: float | None
    above_10pct: bool | None
    above_10pct_after: bool | None


class HelpLink(Contract):
    label: str
    url: str


class Affordability(Contract):
    kwh: Kwh
    kwh_source: Literal["epc_certificate", "estimated"]
    heating_fuel: HeatingFuel
    scenarios: list[Scenario]
    lilee_indicator: bool | None
    help_links: list[HelpLink]
    evidence: list[Evidence]
    fallback_used: bool
