"""Hazard levels from HazardInputs. L3 stub: fixed values; real rules arrive in L4."""

from datetime import UTC, datetime

from app.schemas import HAZARD_ORDER, HazardInputs, HazardLevel, RiskProfile
from app.scoring.config import SURFACE_WATER_LEVEL, SURFACE_WATER_WHY

# A fixed timestamp keeps the stub deterministic.
STUB_GENERATED_AT = datetime(2026, 10, 27, tzinfo=UTC)
STUB_WHY = "Placeholder level until the risk engine is ready."
DATA_SOURCE = {
    "river_sea_flood": "Environment Agency",
    "overheating": "Open-Meteo (CMIP6)",
    "storm": "Open-Meteo (CMIP6)",
    "subsidence": "Your answer",
    "surface_water": "Environment Agency",
}


def assess_risk(inputs: HazardInputs) -> RiskProfile:
    levels = [
        HazardLevel(
            hazard=hazard,
            today="medium",
            y2050="medium",
            why=STUB_WHY,
            data_source=DATA_SOURCE[hazard],
        )
        for hazard in HAZARD_ORDER
    ]
    levels[-1] = levels[-1].model_copy(
        update={
            "today": SURFACE_WATER_LEVEL,
            "y2050": SURFACE_WATER_LEVEL,
            "why": SURFACE_WATER_WHY,
        }
    )
    return RiskProfile(levels=levels, generated_at=STUB_GENERATED_AT)
