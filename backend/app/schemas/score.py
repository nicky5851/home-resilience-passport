from typing import Literal

from pydantic import Field

from app.schemas.base import Band, Contract, ShortText


class ScoreComponent(Contract):
    name: Literal["flood", "heat", "storm", "subsidence", "carbon"]
    points: float
    max_points: float
    reason: ShortText


class ResilienceScore(Contract):
    value: int = Field(ge=0, le=100)
    band: Band
    components: list[ScoreComponent] = []
    version: str
