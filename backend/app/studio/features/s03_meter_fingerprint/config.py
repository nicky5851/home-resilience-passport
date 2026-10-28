"""Constants for the change-point fit (docs/studio/N_20_function.md §S03). Sources noted inline;
items marked **verify** were read from the linked page at build time, not invented."""

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MIN_WINTER_DAYS = 60
WINTER_TEMP_C = 12.0  # a day counts toward the "60 winter days" minimum below this mean temp

# gov.uk gas meter reading guidance (verify, read 2026-10-28):
# https://www.gov.uk/guidance/gas-meter-readings-and-bill-calculation
# volume correction factor 1.02264 x calorific value 39.5 MJ/m3, divided by 3.6 MJ/kWh.
M3_TO_KWH = 1.02264 * 39.5 / 3.6

CHANGE_POINT_MIN_C = 12.0
CHANGE_POINT_MAX_C = 18.0
CHANGE_POINT_STEP_C = 0.5

# System efficiency: kWh of delivered heat per kWh of metered fuel (gas boiler ~85% to flue;
# heat pump expressed as SCOP; direct electric resistance heating is ~100% efficient at point
# of use). These convert metered-fuel slope into delivered-heat HTC.
EFFICIENCY = {"gas": 0.85, "electric_heat_pump": 3.0, "electric_direct": 1.0}

# England 1991-2020 monthly mean temperatures (Met Office UK climate averages, **verify**,
# read 2026-10-28: https://www.metoffice.gov.uk/research/climate/maps-and-data/uk-climate-averages).
# Used only for the secondary "normalised annual heating" stat, not the measured HTC itself;
# a full 30-year ERA5 pull for every upload was judged not worth the extra external call here.
UK_MONTHLY_MEAN_TEMP_C = [5.2, 5.3, 7.0, 9.1, 12.1, 14.9, 17.1, 16.8, 14.3, 11.0, 7.7, 5.5]
DAYS_PER_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

BOOTSTRAP_RESAMPLES = 200
BOOTSTRAP_SEED = 20261028
CI_LOW_PERCENTILE = 2.5
CI_HIGH_PERCENTILE = 97.5

RATING_BANDS = [  # (upper bound W/m2K exclusive, label); last is the catch-all
    (1.0, "excellent"),
    (2.0, "good"),
    (3.0, "average"),
]
RATING_POOR = "poor"
