"""EA NCERM National (2024) (docs/studio/N_20_function.md §S09). Live collection URL and field
names read directly against the OGC API - Features endpoint on 2026-10-28 (not guessed): base
https://environment.data.gov.uk/geoservices/datasets/9fede91f-5acd-4fd2-9bd8-98153fa3c2ff/ogc/features/v1,
with 14 collections named `NCERM_{SMP|NFI}_{2055|2105}_{0|70|95}CC` (SMP = "with shoreline
management plan delivered", NFI = "no future intervention"; CC = climate-change-allowance
percentile) plus `NCERM_Ground_Instability_{Recession,Zone}`. Item properties include
`smp_name`, `mt_smp`/`lt_smp` (medium/long-term policy text). Geometry coordinates are 3D
(lon, lat, 0) - the z is always 0 and dropped on parsing.

Only the 70% central allowance is queried per epoch/scenario (4 collections, not all 12), to
bound the number of outbound calls per page load - logged as a scope call."""

NCERM_BASE = (
    "https://environment.data.gov.uk/geoservices/datasets/"
    "9fede91f-5acd-4fd2-9bd8-98153fa3c2ff/ogc/features/v1"
)
CLIMATE_ALLOWANCE = "70CC"
CLIMATE_LABEL = "70th percentile climate change allowance"

COLLECTIONS: list[dict] = [
    {"epoch": 2055, "scenario": "with_smp", "collection": "NCERM_SMP_2055_70CC"},
    {"epoch": 2105, "scenario": "with_smp", "collection": "NCERM_SMP_2105_70CC"},
    {"epoch": 2055, "scenario": "no_active_intervention", "collection": "NCERM_NFI_2055_70CC"},
    {"epoch": 2105, "scenario": "no_active_intervention", "collection": "NCERM_NFI_2105_70CC"},
]

COASTAL_RADIUS_M = 5000
ITEMS_LIMIT = 40
CACHE_DAYS = 90
MAX_FEATURES = 40
SIMPLIFY_TOLERANCE_DEG = 0.0002

# A small hand-picked set of UK coastline reference points (Estimated - this build did not
# commit the full Natural Earth 10m coastline file the spec names; a coarse nearest-point
# distance is used instead, logged as a scope call), lat/lon only.
COARSE_COASTLINE_POINTS: list[tuple[float, float]] = [
    (50.07, -5.71), (50.13, -5.54), (50.22, -5.05), (50.34, -4.14), (50.37, -3.53),
    (50.61, -2.46), (50.71, -1.98), (50.77, -1.09), (50.80, -0.14), (50.84, 0.29),
    (51.08, 1.15), (51.37, 1.43), (51.95, 1.32), (52.48, 1.75), (52.93, 1.33),
    (53.33, 0.41), (53.74, -0.08), (54.08, -0.07), (54.57, -1.18), (55.02, -1.44),
    (55.62, -1.63), (55.81, -2.07), (56.46, -2.80), (57.14, -2.10), (57.65, -1.78),
    (58.44, -3.08), (58.59, -4.43), (57.94, -5.73), (56.82, -6.11), (56.41, -5.47),
    (55.87, -5.63), (55.46, -5.63), (54.85, -5.13), (54.32, -4.68), (53.41, -4.08),
    (53.21, -4.33), (52.82, -4.75), (52.13, -4.72), (51.70, -5.15), (51.62, -4.17),
    (51.49, -3.18), (51.35, -3.17),
]

ADVICE_LINKS = [
    {
        "label": "Check coastal erosion management in your area",
        "url": "https://www.gov.uk/check-coastal-erosion-management-in-your-area",
    },
    {"label": "Flood Re: what's covered", "url": "https://www.floodre.co.uk/"},
]

SYNTHETIC_COASTAL_THRESHOLD_M = 2000
# Plausible retreat distances (metres) by epoch, used only in the synthetic offline fallback.
SYNTHETIC_RETREAT_M = {2055: 12, 2105: 35}

ERODES_INSURANCE_NOTE = (
    "Coastal erosion is generally not covered by standard home insurance, and Flood Re - the "
    "flood reinsurance scheme - does not cover erosion either (check floodre.co.uk for current "
    "wording)."
)
