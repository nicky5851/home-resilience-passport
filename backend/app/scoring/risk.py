"""Hazard levels from HazardInputs (spec CODING_SPEC.md §6, docs/scoring.md).

Every threshold and weight lives in `app/scoring/config.py`. `today` uses the baseline
inputs, `y2050` uses the 2041-2050 inputs. A missing (`null`) numeric input is scored
`medium` and `why` says the data was unavailable (CONTRACT.md §2 rule 52).
"""

from datetime import UTC, datetime

from app.schemas import HazardInputs, HazardLevel, RiskProfile
from app.scoring.config import (
    FLOOD_BAND_LEVEL,
    FLOOD_WARNING_BUMP,
    HEAT_BUMP_EPC_RATINGS,
    HOT_DAYS_HIGH_ABOVE,
    HOT_DAYS_MEDIUM_FROM,
    SUBSIDENCE_LEVEL,
    SURFACE_WATER_LEVEL,
    SURFACE_WATER_WHY,
    UNKNOWN_LEVEL,
    WIND_HIGH_ABOVE_KMH,
    WIND_MEDIUM_FROM_KMH,
)

# RiskProfile.generated_at records when the real assessment pipeline (N9) built this
# profile, which this pure function cannot know; N9 overwrites it with the real time
# before storing (docs/decisions/L.md). A fixed value here keeps assess_risk deterministic.
RISK_GENERATED_AT = datetime(2026, 10, 27, 9, tzinfo=UTC)

_LEVEL_ORDER = ("low", "medium", "high")

_SUBSIDENCE_WHY = {
    "none_reported": "Based on what you told us, there's no reported subsidence signal.",
    "unknown": "You did not tell us about soil or wall cracks, so this is scored as medium risk.",
    "clay_reported": "You told us the soil here is clay, which raises subsidence risk.",
    "cracks_reported": "You told us about new cracks in the walls, which raises subsidence risk.",
}


def _bump(level: str) -> str:
    """One level up, capped at high (spec §6)."""
    return _LEVEL_ORDER[min(len(_LEVEL_ORDER) - 1, _LEVEL_ORDER.index(level) + 1)]


def _threshold_level(value: float | None, medium_from: float, high_above: float) -> str:
    if value is None:
        return UNKNOWN_LEVEL
    if value < medium_from:
        return "low"
    if value <= high_above:
        return "medium"
    return "high"


def _flood_level(inputs: HazardInputs) -> str:
    level = FLOOD_BAND_LEVEL[inputs.rofrs_band]
    if inputs.active_flood_warnings > 0:
        for _ in range(FLOOD_WARNING_BUMP):
            level = _bump(level)
    return level


def _flood_why(inputs: HazardInputs) -> str:
    band = inputs.rofrs_band
    if band is None:
        why = "Flood data for your postcode is unavailable, so this is scored as medium risk."
    elif band == "none":
        why = "Your postcode is not in the Environment Agency's flood dataset, so this is low risk."
    else:
        why = f"The Environment Agency rates flood risk here as {band.replace('_', ' ')}."
    n = inputs.active_flood_warnings
    if n > 0:
        plural = "" if n == 1 else "s"
        why += f" There {'is' if n == 1 else 'are'} {n} active flood warning{plural} nearby."
    return why


def _heat_bumped(inputs: HazardInputs) -> bool:
    prop = inputs.property
    return bool(prop.top_floor) or prop.epc_rating in HEAT_BUMP_EPC_RATINGS


def _heat_level(value: float | None, bumped: bool) -> str:
    level = _threshold_level(value, HOT_DAYS_MEDIUM_FROM, HOT_DAYS_HIGH_ABOVE)
    return _bump(level) if bumped else level


def _heat_why(inputs: HazardInputs, bumped: bool) -> str:
    baseline, y2050 = inputs.hot_days_baseline, inputs.hot_days_2050
    if baseline is None and y2050 is None:
        why = "Hot-day data for your postcode is unavailable, so this is scored as medium risk."
    elif baseline is None:
        why = f"About {y2050:.0f} hot days a year by 2050; today's figure is unavailable."
    elif y2050 is None:
        why = f"About {baseline:.0f} hot days a year today; the 2050 figure is unavailable."
    else:
        why = f"About {y2050:.0f} hot days a year by 2050, up from {baseline:.0f} today."
    if bumped:
        why += " Raised a level for a top-floor flat or an A/B-rated home."
    return why


def _wind_why(inputs: HazardInputs) -> str:
    baseline, y2050 = inputs.max_wind_baseline_kmh, inputs.max_wind_2050_kmh
    if baseline is None and y2050 is None:
        return "Wind data for your postcode is unavailable, so this is scored as medium risk."
    if baseline is None:
        return f"Strongest winds around {y2050:.0f} km/h by 2050; today's figure is unavailable."
    if y2050 is None:
        return f"Strongest winds around {baseline:.0f} km/h today; the 2050 figure is unavailable."
    return f"Strongest winds around {y2050:.0f} km/h by 2050, from {baseline:.0f} km/h today."


def assess_risk(inputs: HazardInputs) -> RiskProfile:
    flood_level = _flood_level(inputs)
    heat_bumped = _heat_bumped(inputs)
    storm_today = _threshold_level(
        inputs.max_wind_baseline_kmh, WIND_MEDIUM_FROM_KMH, WIND_HIGH_ABOVE_KMH
    )
    storm_2050 = _threshold_level(
        inputs.max_wind_2050_kmh, WIND_MEDIUM_FROM_KMH, WIND_HIGH_ABOVE_KMH
    )
    subsidence_level = SUBSIDENCE_LEVEL[inputs.subsidence_signal]

    levels = [
        HazardLevel(
            hazard="river_sea_flood",
            today=flood_level,
            y2050=flood_level,
            why=_flood_why(inputs),
            data_source="Environment Agency",
        ),
        HazardLevel(
            hazard="overheating",
            today=_heat_level(inputs.hot_days_baseline, heat_bumped),
            y2050=_heat_level(inputs.hot_days_2050, heat_bumped),
            why=_heat_why(inputs, heat_bumped),
            data_source="Open-Meteo (CMIP6)",
        ),
        HazardLevel(
            hazard="storm",
            today=storm_today,
            y2050=storm_2050,
            why=_wind_why(inputs),
            data_source="Open-Meteo (CMIP6)",
        ),
        HazardLevel(
            hazard="subsidence",
            today=subsidence_level,
            y2050=subsidence_level,
            why=_SUBSIDENCE_WHY[inputs.subsidence_signal],
            data_source="Your answer",
        ),
        HazardLevel(
            hazard="surface_water",
            today=SURFACE_WATER_LEVEL,
            y2050=SURFACE_WATER_LEVEL,
            why=SURFACE_WATER_WHY,
            data_source="Environment Agency",
        ),
    ]
    return RiskProfile(levels=levels, generated_at=RISK_GENERATED_AT)
