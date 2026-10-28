"""EA Recorded Flood Outlines (docs/studio/N_20_function.md §S08). Live collection URL and field
names read directly against the OGC API - Features endpoint on 2026-10-28 (not guessed):
base https://environment.data.gov.uk/geoservices/datasets/8c75e700-d465-11e4-8b5b-f0def148f590/ogc/features/v1,
collection id `Recorded_Flood_Outlines`, item properties `name`, `start_date`, `end_date`,
`flood_src` (cause-ish), `data_src` (source)."""

EA_BASE = (
    "https://environment.data.gov.uk/geoservices/datasets/"
    "8c75e700-d465-11e4-8b5b-f0def148f590/ogc/features/v1"
)
EA_COLLECTION = "Recorded_Flood_Outlines"
EA_ITEMS_LIMIT = 50

RADIUS_DEFAULT_M = 1500
RADIUS_MIN_M = 500
RADIUS_MAX_M = 3000

CACHE_DAYS = 30
MAX_EVENTS = 50
MAX_OUTLINE_FEATURES = 30
MAX_OUTLINE_VERTICES = 500
SIMPLIFY_TOLERANCE_DEG = 0.00005

CAVEAT = "Not every flood is recorded. No record does not mean no risk."
WALES_COMING_SOON = "Historic records for Wales are coming soon."
