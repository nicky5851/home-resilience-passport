"""The shared contract in code (spec §4.1, CONTRACT.md). Shared file: change only per spec §3.3."""

from app.schemas.base import (
    Band,
    HazardName,
    IncomeBand,
    Level,
    MeasureCategory,
    Priority,
    PropertyType,
    Tenure,
)
from app.schemas.demo import DemoHome, DemoSlug
from app.schemas.funding import FundingBundle, FundingLine, FundingOption
from app.schemas.hazards import (
    DATA_SOURCES,
    HAZARD_INPUT_RANGES,
    HAZARD_ORDER,
    HazardInputs,
    HazardLevel,
    RiskProfile,
)
from app.schemas.household import Household
from app.schemas.passport import Passport, PassportEvent, PublicPassport
from app.schemas.plan import Measure, Plan, PlanItem
from app.schemas.property import Address, PropertyFacts, normalise_postcode
from app.schemas.score import ResilienceScore, ScoreComponent
from app.schemas.user import UserCreate, UserRead

__all__ = [
    "DATA_SOURCES",
    "HAZARD_INPUT_RANGES",
    "HAZARD_ORDER",
    "Address",
    "Band",
    "DemoHome",
    "DemoSlug",
    "FundingBundle",
    "FundingLine",
    "FundingOption",
    "HazardInputs",
    "HazardLevel",
    "HazardName",
    "Household",
    "IncomeBand",
    "Level",
    "Measure",
    "MeasureCategory",
    "Passport",
    "PassportEvent",
    "Plan",
    "PlanItem",
    "Priority",
    "PropertyFacts",
    "PropertyType",
    "PublicPassport",
    "ResilienceScore",
    "RiskProfile",
    "ScoreComponent",
    "Tenure",
    "UserCreate",
    "UserRead",
    "normalise_postcode",
]
