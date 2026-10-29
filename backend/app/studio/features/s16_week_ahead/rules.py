"""The rules engine (docs/studio/N_20_function.md §S16 Algorithm), pure and tested."""

from app.schemas.base import Level
from app.studio.features.s16_week_ahead.config import (
    FLOOD_RISK_RAIN_ACTION,
    FROST_ACTIONS,
    FROST_MIN_C,
    HARD_FROST_ACTIONS,
    HARD_FROST_MIN_C,
    HEAT_ACTIONS,
    HEAT_HIGH_C,
    HEAT_MAX_C,
    RAIN_ACTIONS,
    RAIN_HIGH_MM,
    RAIN_MM,
    WIND_ACTIONS,
    WIND_GUST_KMH,
    WIND_HIGH_KMH,
)
from app.studio.features.s16_week_ahead.schemas import Alert, Glyph


def glyph_for(
    t_max: float | None, t_min: float | None, rain_mm: float | None, gust: float | None
) -> Glyph:
    if gust is not None and gust >= WIND_GUST_KMH and rain_mm is not None and rain_mm >= RAIN_MM:
        return "storm"
    if t_min is not None and t_min <= FROST_MIN_C:
        return "frost"
    if gust is not None and gust >= WIND_GUST_KMH:
        return "wind"
    if rain_mm is not None and rain_mm >= RAIN_HIGH_MM:
        return "heavy_rain"
    if rain_mm is not None and rain_mm >= 1:
        return "rain"
    if t_max is not None and t_max >= 20:
        return "sun"
    return "cloud"


def frost_alert(t_min: float | None, when: str) -> Alert | None:
    if t_min is None or t_min > FROST_MIN_C:
        return None
    if t_min <= HARD_FROST_MIN_C:
        return Alert(
            kind="hard_frost",
            level="high",
            title="Hard frost",
            actions=[*FROST_ACTIONS, *HARD_FROST_ACTIONS],
            when=when,
        )
    return Alert(
        kind="frost", level="medium", title="Frost", actions=list(FROST_ACTIONS), when=when
    )


def heat_alert(t_max: float | None, top_floor: bool, when: str) -> Alert | None:
    if t_max is None or t_max < HEAT_MAX_C:
        return None
    level: Level = "high" if (t_max >= HEAT_HIGH_C or top_floor) else "medium"
    return Alert(kind="heat", level=level, title="Hot day", actions=list(HEAT_ACTIONS), when=when)


def wind_alert(gust: float | None, high_threshold_at_60: bool, when: str) -> Alert | None:
    if gust is None or gust < WIND_GUST_KMH:
        return None
    level: Level = "high" if (gust >= WIND_HIGH_KMH or high_threshold_at_60) else "medium"
    kind = "strong_wind" if level == "high" else "wind"
    return Alert(kind=kind, level=level, title="Strong wind", actions=list(WIND_ACTIONS), when=when)


def rain_alert(rain_mm: float | None, flood_risk: bool, when: str) -> Alert | None:
    if rain_mm is None or rain_mm < RAIN_MM:
        return None
    level: Level = "high" if rain_mm >= RAIN_HIGH_MM else "medium"
    actions = list(RAIN_ACTIONS)
    if flood_risk:
        actions.append(FLOOD_RISK_RAIN_ACTION)
    return Alert(kind="heavy_rain", level=level, title="Heavy rain", actions=actions, when=when)
