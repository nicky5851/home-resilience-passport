from datetime import date
from typing import Literal

from pydantic import Field

from app.schemas.base import Contract
from app.studio.common.schemas import Evidence
from app.studio.features.s20_portfolio.config import (
    MAX_SCENARIO_YEAR,
    MAX_UPTAKE_PCT,
    MIN_SCENARIO_YEAR,
    MIN_UPTAKE_PCT,
)


class BandCount(Contract):
    band: str
    count: int


class LevelCount(Contract):
    level: Literal["low", "medium", "high"]
    count: int


class District(Contract):
    outcode: str
    lat: float
    lon: float
    count: int
    avg_score: float
    below_c_share_pct: float


class Portfolio(Contract):
    sample_size: int
    generated_on: date
    sample_note: str
    by_epc_band: list[BandCount]
    by_score_band: list[BandCount]
    flood_exposure: list[LevelCount]
    heat_2050: list[LevelCount]
    below_c_share_pct: float
    transition_cost_low_gbp: int
    transition_cost_high_gbp: int
    financed_emissions_t: float
    attribution_note: str
    districts: list[District]
    fairness_note: str
    evidence: list[Evidence]
    fallback_used: Literal[False] = False


class ScenarioRequest(Contract):
    uptake_pct: int = Field(ge=MIN_UPTAKE_PCT, le=MAX_UPTAKE_PCT)
    by_year: int = Field(ge=MIN_SCENARIO_YEAR, le=MAX_SCENARIO_YEAR)


class ScenarioResult(Contract):
    emissions_before_t: float
    emissions_after_t: float
    reduction_pct: float
    below_c_share_after_pct: float
    homes_upgraded: int
    finance_needed_low_gbp: int
    finance_needed_high_gbp: int
