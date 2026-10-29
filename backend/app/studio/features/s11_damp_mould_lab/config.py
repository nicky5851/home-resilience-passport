"""Damp & Mould Lab physics constants (docs/studio/N_20_function.md §S11 Algorithm).

`PropertyFacts` does not surface the EPC's raw wall/window description text, only
`construction_age_band` (RdSAP-style band strings, e.g. "before 1900"), so `wall_u_source` is
always `age_band_default` in this build rather than `epc_description` - a scope call, since
adding a raw-description field would touch the shared `PropertyFacts` schema. U-values below
follow RdSAP 10 default tables (bregroup.com/sap/sap10), **verify** before relying on exact
figures for anything beyond a relative/demo comparison."""

AGE_BAND_WALL_U: dict[str, float] = {
    "before 1900": 2.1,
    "1900-1929": 2.1,
    "1930-1949": 1.5,
    "1950-1966": 1.5,
    "1967-1975": 1.5,
    "1976-1982": 1.0,
    "1983-1990": 0.6,
    "1991-1995": 0.45,
    "1996-2002": 0.45,
    "2003-2006": 0.35,
    "2007 onwards": 0.3,
}
DEFAULT_WALL_U = 1.5

AGE_BAND_WINDOW_U: dict[str, float] = {
    "before 1900": 4.8,
    "1900-1929": 4.8,
    "1930-1949": 4.8,
    "1950-1966": 4.8,
    "1967-1975": 2.8,
    "1976-1982": 2.8,
    "1983-1990": 2.8,
    "1991-1995": 2.8,
    "1996-2002": 2.8,
    "2003-2006": 1.6,
    "2007 onwards": 1.6,
}
DEFAULT_WINDOW_U = 2.8

RSI_WALL = 0.25  # m2K/W, ISO 13788 surface resistance for the mould criterion
RSI_WINDOW = 0.13
CORNER_FRSI_PENALTY = 0.10  # thermal bridge at a cold corner

MOULD_SURFACE_RH = 0.80
WINDOW_CONDENSATION_RH = 1.0

# Excess vapour pressure (Pa) at external temperature <= 0C, by moisture class, falling
# linearly to 0 at 20C.
DELTA_P_AT_ZERO_C: dict[int, float] = {1: 270, 2: 540, 3: 810, 4: 1080}

CACHE_DAYS = 36500  # past weather never changes

LEVEL_LOW_MAX_PCT = 5.0
LEVEL_MEDIUM_MAX_PCT = 20.0

WALL_INSULATION_U = 0.3
DOUBLE_GLAZING_U = 2.8

# **Verified** 2026-10-28: Awaab's Law (Hazards in Social Housing (Prescribed Requirements)
# (England) Regulations 2025) came into force 27 October 2025 for social housing only.
# Extending it to private rented tenancies is, as of this read, still a GOV.UK consultation,
# not yet in force - the private-renter note is worded accordingly.
LANDLORD_TENURES = {"social_renter", "private_renter"}
AWAABS_LAW_URL = "https://www.gov.uk/government/collections/awaabs-law-in-the-social-rented-sector"
LANDLORD_NOTE_BY_TENURE: dict[str, str] = {
    "social_renter": (
        "Your landlord has a legal duty to investigate and fix damp and mould within set "
        "timescales under Awaab's Law. Keep a record of what you report and when."
    ),
    "private_renter": (
        "Awaab's Law currently covers social housing; extending it to private tenancies is "
        "under consultation. Your landlord still has repairing obligations under existing "
        "housing law - keep a record of what you report and when."
    ),
}
