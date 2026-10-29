"""DAQI banding and the airing score (docs/studio/N_20_function.md §S12 Algorithm), pure and
tested."""

from datetime import datetime

from app.studio.features.s12_breathe_easy.config import (
    BRIEF_AIRING_THRESHOLD,
    COOLING_BENEFIT_AFTER_HOUR,
    COOLING_MAX_BONUS,
    COOLING_MIN_DELTA_C,
    COOLING_TARGET_C,
    DAQI_BAND_FOR_INDEX,
    DAQI_MAX_INDEX,
    DAQI_NO2_BOUNDS,
    DAQI_O3_BOUNDS,
    DAQI_PENALTY,
    DAQI_PM10_BOUNDS,
    DAQI_PM25_BOUNDS,
    OPEN_THRESHOLD,
    POLLEN_BOUNDS,
    POLLEN_HIGH_FLOOR,
    POLLEN_PENALTY,
    SCORE_START,
    SUMMER_MONTHS,
    WINTER_DRYING_BONUS,
    WINTER_DRYING_DEW_POINT_MAX_C,
    WINTER_DRYING_HOUR_RANGE,
)


def _sub_index(value: float | None, bounds: list[tuple[int, float]]) -> int | None:
    if value is None:
        return None
    for index, upper in bounds:
        if value <= upper:
            return index
    return DAQI_MAX_INDEX


def daqi_for(
    pm2_5: float | None, pm10: float | None, no2: float | None, o3: float | None
) -> int | None:
    sub_indices = [
        i
        for i in (
            _sub_index(pm2_5, DAQI_PM25_BOUNDS),
            _sub_index(pm10, DAQI_PM10_BOUNDS),
            _sub_index(no2, DAQI_NO2_BOUNDS),
            _sub_index(o3, DAQI_O3_BOUNDS),
        )
        if i is not None
    ]
    return max(sub_indices) if sub_indices else None


def daqi_band(index: int | None) -> str | None:
    return None if index is None else DAQI_BAND_FOR_INDEX[index]


def pollen_level(grains_m3: float | None) -> str | None:
    if grains_m3 is None:
        return None
    if grains_m3 <= 0:
        return "none"
    if grains_m3 >= POLLEN_HIGH_FLOOR:
        return "high"
    for level, upper in POLLEN_BOUNDS:
        if grains_m3 <= upper:
            return level
    return "high"


def score_for(
    *,
    at: datetime,
    daqi_band_value: str | None,
    pollen_level_value: str | None,
    temp_c: float | None,
    dew_point_c: float | None,
    pollution_sensitive: bool,
    pollen_sensitive: bool,
) -> int:
    score = SCORE_START

    if daqi_band_value in DAQI_PENALTY:
        penalty = DAQI_PENALTY[daqi_band_value]
        if pollution_sensitive:
            penalty *= 2
        score -= penalty

    if pollen_level_value in POLLEN_PENALTY:
        penalty = POLLEN_PENALTY[pollen_level_value]
        if pollen_sensitive:
            penalty *= 2
        score -= penalty

    if at.month in SUMMER_MONTHS and at.hour >= COOLING_BENEFIT_AFTER_HOUR and temp_c is not None:
        delta = COOLING_TARGET_C - temp_c
        if delta >= COOLING_MIN_DELTA_C:
            score += min(COOLING_MAX_BONUS, round(delta))
    elif (
        at.month not in SUMMER_MONTHS
        and at.hour in WINTER_DRYING_HOUR_RANGE
        and dew_point_c is not None
        and dew_point_c < WINTER_DRYING_DEW_POINT_MAX_C
    ):
        score += WINTER_DRYING_BONUS

    return max(0, min(100, score))


def advice_for(score: int, is_summer: bool) -> str:
    if score >= OPEN_THRESHOLD:
        return "open" if is_summer else "brief_airing"
    if score >= BRIEF_AIRING_THRESHOLD:
        return "brief_airing"
    return "keep_closed"
