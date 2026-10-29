"""Open-Meteo Air Quality + Forecast APIs and the DEFRA DAQI table (docs/studio/N_20_function.md
§S12). DAQI breakpoints **verified** 2026-10-29 against
https://www.gov.uk/government/publications/health-effects-of-air-pollution/pollutant-concentrations-for-the-daily-air-quality-index-daqi
(24-hr mean PM2.5/PM10, 1-hr mean NO2, 8-hr mean O3; this build uses the hourly concentration
in place of the rolling mean, as the spec itself allows: "hourly concentrations as a proxy").

Pollen bands are **not** an official DEFRA/Met Office published table (none found with exact
numeric thresholds as of this read) - the bands below are an approximation from Met Office
blog figures (grass "high" ~50-150 grains/m3, birch "high" ~81-200 grains/m3), applied
uniformly to grass/birch/alder and flagged Estimated. **Verify** before relying on them."""

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AQ_SOURCE = "Open-Meteo Air Quality API (Copernicus CAMS)"
WEATHER_SOURCE = "Open-Meteo Forecast API"

FORECAST_DAYS = 3
CACHE_HOURS = 1

# (index, upper bound inclusive) ascending; DAQI = max sub-index across pollutants present.
DAQI_PM25_BOUNDS = [
    (1, 11), (2, 23), (3, 35), (4, 41), (5, 47), (6, 53), (7, 58), (8, 64), (9, 70),
]  # fmt: skip
DAQI_PM10_BOUNDS = [
    (1, 16), (2, 33), (3, 50), (4, 58), (5, 66), (6, 75), (7, 83), (8, 91), (9, 100),
]  # fmt: skip
DAQI_NO2_BOUNDS = [
    (1, 67), (2, 134), (3, 200), (4, 267), (5, 334), (6, 400), (7, 467), (8, 534), (9, 600),
]  # fmt: skip
DAQI_O3_BOUNDS = [
    (1, 33), (2, 66), (3, 100), (4, 120), (5, 140), (6, 160), (7, 187), (8, 213), (9, 240),
]  # fmt: skip
DAQI_MAX_INDEX = 10

DAQI_BAND_FOR_INDEX: dict[int, str] = {
    **{i: "low" for i in (1, 2, 3)},
    **{i: "moderate" for i in (4, 5, 6)},
    **{i: "high" for i in (7, 8, 9)},
    10: "very_high",
}

# Anything at or above the "high" lower bound stays "high" - the spec's own pollen_level
# literal has no "very high" tier.
POLLEN_BOUNDS: list[tuple[str, float]] = [("low", 30), ("moderate", 50)]
POLLEN_HIGH_FLOOR = 50

SCORE_START = 100
DAQI_PENALTY = {"moderate": 30, "high": 60, "very_high": 90}
POLLEN_PENALTY = {"moderate": 20, "high": 40}

SUMMER_MONTHS = {5, 6, 7, 8, 9}
COOLING_BENEFIT_AFTER_HOUR = 18
COOLING_TARGET_C = 22.0
COOLING_MIN_DELTA_C = 2.0
COOLING_MAX_BONUS = 20

WINTER_DRYING_HOUR_RANGE = range(10, 15)
WINTER_DRYING_DEW_POINT_MAX_C = 5.0
WINTER_DRYING_BONUS = 10

OPEN_THRESHOLD = 70
BRIEF_AIRING_THRESHOLD = 40
MIN_WINDOW_HOURS = 2
