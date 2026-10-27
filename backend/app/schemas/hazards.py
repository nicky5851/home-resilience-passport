from datetime import datetime
from typing import Literal

from app.schemas.base import Contract, HazardName, Level, ShortText
from app.schemas.property import PropertyFacts

# CONTRACT §2: valid range of every numeric HazardInputs field (inclusive).
HAZARD_INPUT_RANGES: dict[str, tuple[float, float]] = {
    "active_flood_warnings": (0, 50),
    "hot_days_baseline": (0, 60),
    "hot_days_2050": (0, 90),
    "heavy_rain_days_baseline": (0, 40),
    "heavy_rain_days_2050": (0, 50),
    "max_wind_baseline_kmh": (10, 150),
    "max_wind_2050_kmh": (10, 150),
}

# CONTRACT §2: the only allowed HazardLevel.data_source strings.
DATA_SOURCES = (
    "Environment Agency",
    "Open-Meteo (CMIP6)",
    "EPC register",
    "Our EPC model",
    "Your answer",
)

# CONTRACT §2: RiskProfile.levels always holds the five hazards in this order.
HAZARD_ORDER: tuple[HazardName, ...] = (
    "river_sea_flood",
    "overheating",
    "storm",
    "subsidence",
    "surface_water",
)


class HazardInputs(Contract):
    rofrs_band: Literal["high", "medium", "low", "very_low", "none"] | None = None
    active_flood_warnings: int = 0
    hot_days_baseline: float | None = None
    hot_days_2050: float | None = None
    heavy_rain_days_baseline: float | None = None
    heavy_rain_days_2050: float | None = None
    max_wind_baseline_kmh: float | None = None
    max_wind_2050_kmh: float | None = None
    subsidence_signal: Literal["clay_reported", "cracks_reported", "none_reported", "unknown"] = (
        "unknown"
    )
    property: PropertyFacts


class HazardLevel(Contract):
    hazard: HazardName
    today: Level
    y2050: Level
    why: ShortText
    data_source: str


class RiskProfile(Contract):
    levels: list[HazardLevel] = []
    generated_at: datetime
