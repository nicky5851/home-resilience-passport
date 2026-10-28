"""Peer definition and upgrade-inference rules (docs/studio/N_20_function.md §S02).

Fully configurable so A or N can tune thresholds without touching the algorithm.
"""

RADIUS_DEFAULT_M = 1000
RADIUS_MIN_M = 250
RADIUS_MAX_M = 2000
NEAREST_POSTCODES_LIMIT = 50
FETCH_CONCURRENCY = 5
FETCH_BUDGET_S = 12.0

MIN_PEERS_FOR_STORIES = 5  # k-anonymity (spec §1.6)
IMPROVER_SAP_GAIN = 5
MAX_STORIES = 6
MAX_UPGRADE_ROWS = 6

# Oldest -> newest; "±1 band" peer matching walks this list.
AGE_BAND_ORDER = [
    "before 1900",
    "1900-1929",
    "1930-1949",
    "1950-1966",
    "1967-1975",
    "1976-1982",
    "1983-1990",
    "1991-1995",
    "1996-2002",
    "2003-2006",
    "2007-2011",
    "2012 onwards",
]

FUEL_FAMILIES = {
    "mains gas": "gas",
    "lpg": "gas",
    "electric": "electric",
    "oil": "oil",
}


def fuel_family(fuel: str | None) -> str:
    if not fuel:
        return "unknown"
    low = fuel.lower()
    for key, family in FUEL_FAMILIES.items():
        if key in low:
            return family
    return "other"


UPGRADE_RULES: list[tuple[str, str]] = [
    # (label, detector name) — detectors live in service.py; order is display order.
    ("Wall insulation", "wall_insulation"),
    ("Loft insulation", "loft_insulation"),
    ("Double/triple glazing", "glazing"),
    ("Heat pump", "heat_pump"),
    ("Solar PV", "solar_pv"),
    ("LED lighting", "led_lighting"),
    ("Boiler upgrade", "boiler_upgrade"),
]
