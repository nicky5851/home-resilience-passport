"""Loads the committed sample once per process (docs/studio/N_20_function.md §S20 step 2)."""

import json
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

from app.schemas import PropertyFacts
from app.schemas.hazards import RiskProfile
from app.schemas.score import ResilienceScore
from app.studio.features.s20_portfolio.config import DATA_PATH


@dataclass(frozen=True)
class Transition:
    cost_low_gbp: int
    cost_high_gbp: int
    co2_saved_kg_per_year: int
    reached_c: bool


@dataclass(frozen=True)
class PortfolioHome:
    outcode: str
    property: PropertyFacts
    risk: RiskProfile
    score: ResilienceScore
    transition: Transition


@dataclass(frozen=True)
class PortfolioData:
    generated_on: date
    seed: int
    homes: tuple[PortfolioHome, ...]
    district_centroids: dict[str, tuple[float, float]]


@lru_cache(maxsize=1)
def load() -> PortfolioData:
    raw = json.loads(DATA_PATH.read_text())
    homes = tuple(
        PortfolioHome(
            outcode=h["outcode"],
            property=PropertyFacts.model_validate(h["property"]),
            risk=RiskProfile.model_validate(h["risk"]),
            score=ResilienceScore.model_validate(h["score"]),
            transition=Transition(**h["transition"]),
        )
        for h in raw["homes"]
    )
    centroids = {k: (v[0], v[1]) for k, v in raw["district_centroids"].items()}
    return PortfolioData(
        generated_on=date.fromisoformat(raw["generated_on"]),
        seed=raw["seed"],
        homes=homes,
        district_centroids=centroids,
    )
