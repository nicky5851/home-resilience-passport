from typing import Literal

from pydantic import Field

from app.schemas.base import Contract, IncomeBand, Priority, Tenure


class Household(Contract):
    tenure: Tenure
    income_band: IncomeBand
    budget_gbp: int = Field(ge=0, le=100_000)
    priorities: list[Priority] = Field(default_factory=list, max_length=3)
    # Over 75, disability, long-term illness or young children. None = prefer not to say.
    # Special category data (CONTRACT §6): never logged, never sent to the LLM.
    vulnerable: bool | None = None
    # Stored only; nothing is ever sent to Lloyds.
    consent_lloyds_data: bool = False
    # "Have you noticed new cracks in the walls, or been told the ground is clay?" (optional).
    # Becomes HazardInputs.subsidence_signal: yes → cracks_reported, no → none_reported.
    subsidence_signal: Literal["yes", "no", "unknown"] = "unknown"
