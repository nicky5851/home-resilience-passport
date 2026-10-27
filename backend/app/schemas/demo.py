from typing import Literal

from app.schemas.base import Contract
from app.schemas.funding import FundingBundle
from app.schemas.hazards import RiskProfile
from app.schemas.household import Household
from app.schemas.plan import Plan
from app.schemas.property import Address, PropertyFacts
from app.schemas.score import ResilienceScore

DemoSlug = Literal[
    "flood-terrace", "coastal-bungalow", "city-top-flat", "clay-semi", "rural-cottage"
]


class DemoHome(Contract):
    slug: DemoSlug
    hazard_shown: Literal["river_sea_flood", "overheating", "storm", "subsidence", "low_risk"]
    address: Address
    household: Household
    property: PropertyFacts
    risk: RiskProfile
    score: ResilienceScore
    plan: Plan
    funding: FundingBundle
