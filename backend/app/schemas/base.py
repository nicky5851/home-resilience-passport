"""Shared building blocks for the contract models (CONTRACT.md §1)."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

Level = Literal["low", "medium", "high"]
Band = Literal["A", "B", "C", "D", "E", "F", "G"]
HazardName = Literal["river_sea_flood", "overheating", "storm", "subsidence", "surface_water"]
MeasureCategory = Literal["flood", "heat", "storm", "subsidence", "carbon"]
PropertyType = Literal["detached", "semi_detached", "terraced", "flat", "bungalow", "other"]
Tenure = Literal["owner_occupier", "landlord", "private_renter", "social_renter"]
IncomeBand = Literal["under_20k", "20k_40k", "40k_60k", "60k_100k", "over_100k"]
Priority = Literal["lower_bills", "comfort", "flood_safety", "lower_carbon", "home_value"]

# CONTRACT §1 rule 8: text shown to users is at most 140 characters (explanations 200).
ShortText = Annotated[str, StringConstraints(max_length=140)]
ExplanationText = Annotated[str, StringConstraints(max_length=200)]


class Contract(BaseModel):
    """Base for every contract model: unknown keys are rejected so typos fail loudly."""

    model_config = ConfigDict(extra="forbid")
