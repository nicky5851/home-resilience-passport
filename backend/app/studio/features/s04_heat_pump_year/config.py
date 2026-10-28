"""Sourced constants for the heat-pump-year simulation (docs/studio/N_20_function.md §S04).
Figures marked **verify** were read live on 2026-10-28 and should be re-checked each quarter."""

# RdSAP age-band HLP defaults, W/m2K (Estimated, a rough guide - config.py per the spec).
HLP_BY_AGE_BAND: dict[str, float] = {
    "before 1900": 3.0,
    "1900-1929": 2.8,
    "1930-1949": 2.6,
    "1950-1966": 2.4,
    "1967-1975": 2.1,
    "1976-1982": 1.8,
    "1983-1990": 1.6,
    "1991-1995": 1.4,
    "1996-2002": 1.2,
    "2003-2006": 1.0,
    "2007-2011": 0.9,
    "2012 onwards": 0.8,
}
HLP_DEFAULT = 2.0

FORM_FACTOR: dict[str, float] = {
    "detached": 1.0,
    "semi-detached": 0.9,
    "end-terrace": 0.9,
    "mid-terrace": 0.8,
    "bungalow": 1.05,
    "flat": 0.7,
}
FORM_FACTOR_DEFAULT = 0.9

T_SET_DAY_C = 20.0
T_SET_NIGHT_C = 17.0
DAY_START_HOUR = 7
DAY_END_HOUR = 22
INTERNAL_GAIN_K = 2.0

COP_COEFFICIENT = 0.45
COP_MIN, COP_MAX = 1.5, 5.5
DEFROST_LOW_C, DEFROST_HIGH_C = -2.0, 5.0
DEFROST_PENALTY = 0.10

DESIGN_OUTDOOR_C = -2.0
DESIGN_INDOOR_C = 21.0
SIZE_STEPS_KW = [4, 5, 6, 8, 10, 12, 14, 16]

BOILER_EFFICIENCY = 0.90

# Ofgem Direct Debit price-cap average, 1 Oct-31 Dec 2026 (**verify** quarterly):
# https://www.ofgem.gov.uk/information-consumers/energy-advice-households/energy-price-cap-unit-rates-and-standing-charges
# read 2026-10-28.
GAS_P_PER_KWH = 7.97
ELEC_P_PER_KWH = 26.32
GAS_STANDING_P_PER_DAY = 29.68
ELEC_STANDING_P_PER_DAY = 54.83

# Boiler Upgrade Scheme standard grant (**verify**): https://www.gov.uk/apply-boiler-upgrade-scheme,
# read 2026-10-28 (Energy Saving Trust corroborates £7,500 for air/ground/water source heat pumps;
# an off-gas-grid higher rate of £9,000 may apply and is not modelled here).
BUS_GRANT_GBP = 7500

# DESNZ 2026 government GHG conversion factors, kg CO2e/kWh (**verify** against the official
# workbook; cited via a third-party summary of 'UK electricity'!E25 and 'Fuels'!D42,
# read 2026-10-28).
CO2_KG_PER_KWH_ELEC = 0.13096
CO2_KG_PER_KWH_GAS = 0.18231

# MCS Data Dashboard average installed ASHP cost is reported around £12,944 (Jan-Jul 2025 data);
# commercial guides give a 2026 planning range of about £8,000-£14,000 (**verify**),
# https://datadashboard.mcscertified.com/, read 2026-10-28.
INSTALL_COST_LOW_GBP = 8000
INSTALL_COST_HIGH_GBP = 14000

ERA5_CACHE_DAYS = 365
