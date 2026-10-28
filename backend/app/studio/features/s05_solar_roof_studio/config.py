"""Sourced constants for the solar roof studio (docs/studio/N_20_function.md §S05). Figures
marked **verify** were read live on 2026-10-28 and should be re-checked periodically."""

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"
PVGIS_LOSS_PERCENT = 14
PVGIS_CACHE_DAYS = 365

ASPECT_MIN, ASPECT_MAX = -180, 180
PITCH_MIN, PITCH_MAX = 0, 60
KWP_MIN, KWP_MAX = 0.5, 12.0

ROOF_USABLE_FRACTION = 0.70
ROOF_KWP_PER_M2 = 0.20
ROOF_KWP_CAP = 6.0
STOREYS_BY_PROPERTY_TYPE: dict[str, int] = {
    "detached": 2,
    "semi_detached": 2,
    "terraced": 2,
    "bungalow": 1,
    "flat": 2,
    "other": 2,
}

ROSE_ASPECTS_DEG = [-180, -135, -90, -45, 0, 45, 90, 135]

# Self-use fraction by battery size (Energy Saving Trust solar guidance, **verify**):
# https://energysavingtrust.org.uk/advice/solar-panels/, read 2026-10-28.
SELF_USE_FRACTION: dict[int, float] = {0: 0.40, 5: 0.65, 10: 0.75}

# Ofgem Direct Debit price-cap import rate, Oct-Dec 2026 (**verify** quarterly), same source
# as S04's config.py: https://www.ofgem.gov.uk/information-consumers/energy-advice-households/energy-price-cap-unit-rates-and-standing-charges
IMPORT_P_PER_KWH = 26.32

# No single Ofgem "guide rate" exists for the Smart Export Guarantee - suppliers set their own
# tariffs, which in late 2026 range roughly 4p-30p/kWh depending on fixed vs battery-linked
# deals. 15.0p is a representative mid-range fixed-tariff figure (**verify**, user can
# override via `export_p_per_kwh`): https://www.ofgem.gov.uk/environmental-and-social-schemes/smart-export-guarantee-seg,
# read 2026-10-28.
EXPORT_P_PER_KWH_DEFAULT = 15.0

# MCS/DESNZ-derived average installed cost, 2026 (**verify**): roughly £1,500-£2,000 per kWp,
# https://datadashboard.mcscertified.com/, read 2026-10-28.
INSTALL_COST_LOW_GBP_PER_KWP = 1500
INSTALL_COST_HIGH_GBP_PER_KWP = 2000

LIFETIME_YEARS = 25
DEGRADATION_PER_YEAR = 0.005

# DESNZ 2026 grid electricity factor, same source as S04's config.py.
CO2_KG_PER_KWH_ELEC = 0.13096

PANEL_KWP = 0.43

SUITABILITY_GOOD_KWH_PER_KWP = 900
SUITABILITY_FAIR_KWH_PER_KWP = 750
