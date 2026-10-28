"""Event catalogue for Storm Replay (docs/studio/N_20_function.md §S07). Every date **verified**
against Met Office / press reporting on 2026-10-28; Storm Darragh's peak-impact window was
re-checked directly against the Met Office's own report during this build
(https://www.metoffice.gov.uk/weather/warnings-and-advice/uk-storm-centre/index)."""

from datetime import date

EVENTS: list[dict] = [
    {
        "id": "storm-dennis-2020",
        "name": "Storm Dennis",
        "kind": "wind",
        "start_date": date(2020, 2, 15),
        "end_date": date(2020, 2, 16),
    },
    {
        "id": "storm-arwen-2021",
        "name": "Storm Arwen",
        "kind": "wind",
        "start_date": date(2021, 11, 26),
        "end_date": date(2021, 11, 27),
    },
    {
        "id": "storm-eunice-2022",
        "name": "Storm Eunice",
        "kind": "wind",
        "start_date": date(2022, 2, 18),
        "end_date": date(2022, 2, 18),
    },
    {
        "id": "heatwave-2022",
        "name": "The July 2022 heatwave",
        "kind": "heat",
        "start_date": date(2022, 7, 18),
        "end_date": date(2022, 7, 19),
    },
    {
        "id": "storm-babet-2023",
        "name": "Storm Babet",
        "kind": "rain",
        "start_date": date(2023, 10, 18),
        "end_date": date(2023, 10, 21),
    },
    {
        "id": "storm-ciaran-2023",
        "name": "Storm Ciarán",
        "kind": "wind",
        "start_date": date(2023, 11, 1),
        "end_date": date(2023, 11, 2),
    },
    {
        "id": "storm-darragh-2024",
        "name": "Storm Darragh",
        "kind": "wind",
        "start_date": date(2024, 12, 6),
        "end_date": date(2024, 12, 7),
    },
    {
        "id": "storm-eowyn-2025",
        "name": "Storm Éowyn",
        "kind": "wind",
        "start_date": date(2025, 1, 24),
        "end_date": date(2025, 1, 24),
    },
]

WINDOW_PAD_DAYS = 1
ERA5_CACHE_FOREVER_DAYS = 36500  # past weather never changes

WIND_SEVERITY_DIVISOR_KMH = 120.0
RAIN_SEVERITY_DIVISOR_MM = 60.0
HEAT_SEVERITY_BASE_C = 25.0
HEAT_SEVERITY_DIVISOR_C = 15.0

# One-node indoor model time constants (hours), by construction (Estimated, a rough guide).
TAU_HOURS_BY_CONSTRUCTION: dict[str, float] = {
    "solid_masonry": 30.0,
    "cavity": 18.0,
    "timber_or_flat": 10.0,
}
TAU_DEFAULT = 18.0

SOLAR_GAIN_K_PER_HOUR = 0.6
SOLAR_GAIN_START_HOUR = 10
SOLAR_GAIN_END_HOUR = 18
TOP_FLOOR_FLAT_GAIN_MULTIPLIER = 1.5
SHADING_GAIN_MULTIPLIER = 0.5
NIGHT_VENT_START_HOUR = 22
NIGHT_VENT_END_HOUR = 7
NIGHT_VENT_TAU_DIVISOR = 3.0

GUTTER_OVERFLOW_RAIN_MM_PER_H = 4.0
MAX_PEAK_MOMENTS = 4
MAX_LESSONS = 4

LESSON_CATEGORY_BY_KIND: dict[str, str] = {"wind": "storm", "rain": "flood", "heat": "heat"}
