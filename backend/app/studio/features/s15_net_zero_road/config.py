"""Grid decarbonisation and residential pathway data (docs/studio/N_20_function.md §S15).

- `grid_factors.csv`: the domestic, consumption-based *long-run marginal* electricity emissions
  factor, kgCO2e/kWh, for every year 2025-2050 - **verified** 2026-10-29 by downloading
  `data-tables-1-19.xlsx` (Table 1) from the GOV.UK page for "Valuation of energy use and
  greenhouse gas emissions for appraisal" (BEIS modelling, tables last revised November 2023):
  https://www.gov.uk/government/publications/valuation-of-energy-use-and-greenhouse-gas-emissions-for-appraisal
- Fuel emission factors (`FUEL_FACTOR_KG_PER_KWH`) are constant across years and **verified**
  2026-10-29 from the DESNZ 2025 GHG Conversion Factors flat-format file (Scope 1 combustion,
  kWh Gross CV): natural gas 0.18296, LPG 0.2145, "Burning oil" (home heating oil, not road
  diesel/"Gas oil") 0.24677 kg CO2e/kWh.
  https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025
- `ccc_pathway.csv`: an index of residential building emissions vs 2025 (2025=100). The CCC's
  Seventh Carbon Budget (Feb 2025) publishes a 66% residential cut by 2040 and "near-complete"
  decarbonisation by 2050 as its headline residential figures, but no year-by-year dataset for
  this could be found as a direct download this session (**scope call** - the CSV's 2030/2035/
  2045 points are a smooth curve fitted through the two published headline anchors, not CCC's
  own underlying model output; treat the pathway line as illustrative only).
  https://www.theccc.org.uk/publication/the-seventh-carbon-budget/

`measures.csv` (owned by A) has no heat-pump or solar-PV row today, so the SCOP-conversion and
self-generation branches below are implemented per the spec's algorithm but are not reachable
through the real reference data - a scope note, not a bug. `ELECTRICITY_SAVING_MEASURE_IDS`
is a small heuristic for which of today's two bill-saving measures displaces electricity (and
should be re-scaled by the grid factor over time) vs gas (constant fuel factor): led-lighting
is electricity, loft-insulation is heating fuel."""

import csv
from pathlib import Path

GRID_FACTORS_CSV = Path(__file__).resolve().parents[2] / "data" / "grid_factors.csv"
CCC_PATHWAY_CSV = Path(__file__).resolve().parents[2] / "data" / "ccc_pathway.csv"

YEAR_MIN = 2025
YEAR_MAX = 2050
MAX_STEPS = 12
NEAR_ZERO_THRESHOLD_KG = 500

FUEL_FACTOR_KG_PER_KWH: dict[str, float] = {
    "gas": 0.18296,
    "oil": 0.24677,
    "lpg": 0.2145,
}

HEAT_PUMP_SCOP = 3.0
SOLAR_KWH_PER_KWP = 850
SOLAR_DEFAULT_KWP = 3
SOLAR_SELF_USE_PCT = 0.40

HEAT_PUMP_MEASURE_IDS = {"heat-pump", "heat-pump-install", "air-source-heat-pump"}
SOLAR_MEASURE_IDS = {"solar", "solar-pv", "solar-panels"}
ELECTRICITY_SAVING_MEASURE_IDS = {"led-lighting"}

DEFAULT_STEPS_LIMIT = 5
DEFAULT_STEPS_SPACING_YEARS = 3


def _load_year_series(path: Path, value_col: str) -> list[tuple[int, float]]:
    with path.open(newline="") as f:
        return [(int(row["year"]), float(row[value_col])) for row in csv.DictReader(f)]


def load_grid_factors() -> list[tuple[int, float]]:
    return _load_year_series(GRID_FACTORS_CSV, "kg_co2e_per_kwh")


def load_ccc_pathway() -> list[tuple[int, float]]:
    return _load_year_series(CCC_PATHWAY_CSV, "index_vs_2025")
