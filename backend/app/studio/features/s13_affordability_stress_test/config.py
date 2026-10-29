"""Price-cap scenarios and energy-cost maths (docs/studio/N_20_function.md §S13).

Rates in `app/studio/data/price_cap.csv` are **verified** 2026-10-29 for "today" (Ofgem's
October-December 2026 cap, ofgem.gov.uk/energy-price-cap) and "peak_2022" (the Energy Price
Guarantee rates actually paid from October 2022, the GOV.UK factsheet); "pre_crisis_2021" uses
Oct 2020-Mar 2021 period-average unit rates from an ICAEW chart (no exact April 2021 cap
unit-rate table was found in this session) - **verify** before relying on it beyond a rough
comparison. Oil/LPG per-kWh prices are a rough placeholder, not read from DESNZ's quarterly
energy prices tables this session - **verify** before relying on them.

`PropertyFacts` does not surface the EPC's raw `energy-consumption-current` kWh/m2 field (only
`epc_score`, a 0-100 SAP-style score), so `kwh_source` is always `estimated` in this build - a
scope call, consistent with [[s11-u-value-scope]]."""

import csv
from pathlib import Path

PRICE_CAP_CSV = Path(__file__).resolve().parents[2] / "data" / "price_cap.csv"

OIL_P_PER_KWH = 7.0
LPG_P_PER_KWH = 9.5
OIL_LPG_SOURCE_URL = "https://www.gov.uk/government/collections/quarterly-energy-prices"

# kWh/m2/yr space-heating-equivalent defaults by construction age band (Estimated - rough
# RdSAP-shaped figures for older vs newer fabric, not a published table read this session).
AGE_BAND_KWH_PER_M2: dict[str, float] = {
    "before 1900": 220,
    "1900-1929": 220,
    "1930-1949": 190,
    "1950-1966": 170,
    "1967-1975": 150,
    "1976-1982": 130,
    "1983-1990": 110,
    "1991-1995": 100,
    "1996-2002": 90,
    "2003-2006": 75,
    "2007 onwards": 60,
}
DEFAULT_KWH_PER_M2 = 150
DEFAULT_FLOOR_AREA_M2 = 85.0
ELECTRICITY_ONLY_SHARE = 1.0
GAS_HEATING_ELECTRICITY_SHARE = 0.15  # lighting/appliances baseload alongside gas heating

FUEL_FOR_MAIN_FUEL: dict[str, str] = {
    "mains gas": "gas",
    "electricity": "electric",
    "oil": "oil",
    "LPG": "lpg",
}
DEFAULT_HEATING_FUEL = "gas"

SCENARIOS = [
    {"id": "today", "label": "Today's price cap"},
    {"id": "peak_2022", "label": "2022-23 winter peak"},
    {"id": "shock_30", "label": "A 30% price shock"},
    {"id": "pre_crisis_2021", "label": "Pre-crisis (2021)"},
]
SHOCK_30_MULTIPLIER = 1.3

INCOME_BAND_MIDPOINT_GBP: dict[str, int] = {
    "under_20k": 15_000,
    "20k_40k": 30_000,
    "40k_60k": 50_000,
    "60k_100k": 80_000,
    "over_100k": 120_000,
}
AFFORDABILITY_PCT_THRESHOLD = 10.0
LILEE_BANDS = {"D", "E", "F", "G"}
LILEE_INCOME_BAND = "under_20k"

HELP_LINKS = [
    {
        "label": "Citizens Advice: help with energy bills",
        "url": "https://www.citizensadvice.org.uk/consumer/energy/energy-supply/get-help-paying-your-bills/",
    },
    {"label": "Warm Home Discount", "url": "https://www.gov.uk/the-warm-home-discount-scheme"},
    {"label": "Simple Energy Advice", "url": "https://www.gov.uk/improve-energy-efficiency"},
    {
        "label": "Talk to us if you're worried (illustrative)",
        "url": "https://www.lloydsbank.com/current-accounts/managing-your-money/money-worries.html",
    },
]


def load_price_cap() -> dict[str, dict[str, float]]:
    rows: dict[str, dict[str, float]] = {}
    with PRICE_CAP_CSV.open(newline="") as f:
        for row in csv.DictReader(f):
            rows[row["period_start"]] = {
                "gas_p_per_kwh": float(row["gas_p_per_kwh"]),
                "elec_p_per_kwh": float(row["elec_p_per_kwh"]),
                "gas_standing_p_per_day": float(row["gas_standing_p_per_day"]),
                "elec_standing_p_per_day": float(row["elec_standing_p_per_day"]),
            }
    return rows
