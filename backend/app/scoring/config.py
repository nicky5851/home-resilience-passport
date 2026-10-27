"""Every threshold and weight scoring uses (spec §6, §7 Funding). L owns this file.

Tests import these same constants, so changing a number here never needs a test edit.
"""

from typing import Literal

SCORING_VERSION = "v1"

# --- Risk levels (spec §6) ----------------------------------------------------------------
# River/sea flood: RoFRS band -> level. None (unknown) is scored medium (CONTRACT §2).
FLOOD_BAND_LEVEL: dict[str | None, str] = {
    "none": "low",
    "very_low": "low",
    "low": "medium",
    "medium": "high",
    "high": "high",
    None: "medium",
}
FLOOD_WARNING_BUMP = 1  # +1 level if any active warning (capped at high)

# Overheating: hot days per year (≥ 28 °C, CONTRACT §2). low < 5, medium 5–15, high > 15.
HOT_DAYS_MEDIUM_FROM = 5
HOT_DAYS_HIGH_ABOVE = 15
HEAT_BUMP_EPC_RATINGS = ("A", "B")  # +1 level for top-floor flats or A/B-rated homes

# Storm: sustained 10 m wind (not gusts), km/h. low < 50, medium 50–65, high > 65.
WIND_MEDIUM_FROM_KMH = 50
WIND_HIGH_ABOVE_KMH = 65

SUBSIDENCE_LEVEL: dict[str, str] = {
    "none_reported": "low",
    "unknown": "medium",
    "clay_reported": "high",
    "cracks_reported": "high",
}

UNKNOWN_LEVEL = "medium"
SURFACE_WATER_LEVEL = "medium"  # M1: no data yet (CONTRACT §2)
SURFACE_WATER_WHY = "Surface-water data is coming in a later version"

# --- Score (spec §6) ----------------------------------------------------------------------
ComponentName = Literal["flood", "heat", "storm", "subsidence", "carbon"]

MAX_POINTS: dict[ComponentName, float] = {
    "flood": 30,
    "heat": 20,
    "storm": 10,
    "subsidence": 10,
    "carbon": 30,
}
HAZARD_COMPONENT: dict[str, ComponentName] = {
    "river_sea_flood": "flood",
    "overheating": "heat",
    "storm": "storm",
    "subsidence": "subsidence",
}
LEVEL_FRACTION: dict[str, float] = {"low": 1.0, "medium": 0.5, "high": 0.1}

CARBON_POINTS_PER_EPC_POINT = 0.3
EPC_BAND_MIDPOINT: dict[str, int] = {"A": 96, "B": 86, "C": 75, "D": 61, "E": 47, "F": 30, "G": 10}
CARBON_POINTS_UNKNOWN = 15.0

# Lowest score for each band, best first; anything lower is G.
SCORE_BANDS: tuple[tuple[str, int], ...] = (
    ("A", 85),
    ("B", 70),
    ("C", 55),
    ("D", 40),
    ("E", 25),
    ("F", 10),
)

# --- Funding (spec §7) --------------------------------------------------------------------
FUNDING_KIND_ORDER: dict[str, int] = {
    "grant": 0,
    "cashback": 1,
    "insurance_discount": 2,
    "loan": 3,
    "mortgage_further_advance": 3,
}
LOAN_TERM_MONTHS = 60  # monthly cost over 5 years
