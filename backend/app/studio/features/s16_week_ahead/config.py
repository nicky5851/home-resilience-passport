"""Open-Meteo UK Met Office forecast adapter and alert thresholds (docs/studio/N_20_function.md
§S16).

**Verified** 2026-10-29 via curl against `https://api.open-meteo.com/v1/forecast`:
`models=ukmo_seamless` returns full 7-day `temperature_2m_max`, `temperature_2m_min`,
`precipitation_sum` and `wind_gusts_10m_max` (the final day is `null`, a normal forecast-horizon
edge, not a model gap), but `uv_index_max` is mostly `null` beyond ~day 2 under that model - the
UKMO model itself doesn't carry a UV product, so Open-Meteo pads it. Rather than swap the whole
request to `best_match` whenever UV is missing (which would also lose the UKMO-specific
temperature/wind/rain), a single request names both models
(`models=ukmo_seamless,best_match`), which returns suffixed fields
(`temperature_2m_max_ukmo_seamless`, `temperature_2m_max_best_match`, ...); each field uses its
`_ukmo_seamless` value when present and falls back to `_best_match` per field, per day.

No snowfall variable is fetched, so the `snow` glyph is never produced - a scope call, since the
spec's glyph enum includes it but no UK winter snow model was wired up this session.

The "rural" qualifier for the high-wind-at-60-km/h threshold has no `PropertyFacts` field to
read, so it is approximated here as the home's own `storm` hazard level being "high" - a scope
call, since there is no direct rural/urban flag in the contract."""

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
PRIMARY_MODEL = "ukmo_seamless"
FALLBACK_MODEL = "best_match"
MODEL_LABEL = "Met Office UKV via Open-Meteo"
SOURCE_URL = "https://open-meteo.com/en/docs/ukmo-api"

DAILY_VARS = (
    "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_gusts_10m_max,uv_index_max"
)
FORECAST_DAYS = 7
CACHE_HOURS = 1

FROST_MIN_C = 0.0
HARD_FROST_MIN_C = -3.0
HEAT_MAX_C = 27.0
HEAT_HIGH_C = 30.0
WIND_GUST_KMH = 60.0
WIND_HIGH_KMH = 80.0
RAIN_MM = 15.0
RAIN_HIGH_MM = 30.0

FROST_ACTIONS = ["Lag outside taps", "Set your heating to its frost-protect setting"]
HARD_FROST_ACTIONS = [
    "Open the loft hatch so pipes up there stay warm",
    "Check on elderly neighbours",
]
HEAT_ACTIONS = [
    "Close blinds on sunny-facing windows by 10:00",
    "Open windows after 21:00 once it cools down",
]
TOP_FLOOR_HEAT_NOTE = "Top-floor flats heat up fastest - treat 27°C as a high-heat day here."
WIND_ACTIONS = ["Secure bins, the trampoline and any garden furniture"]
RAIN_ACTIONS = ["Clear gutters and drains before the rain arrives"]
FLOOD_RISK_RAIN_ACTION = "Check the Environment Agency's live flood warnings for your area"
