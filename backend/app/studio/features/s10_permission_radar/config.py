"""Planning Data platform (MHCLG) datasets and the permitted-development rule table
(docs/studio/N_20_function.md §S10). Dataset ids and the containment-query behaviour verified
directly against https://www.planning.data.gov.uk/entity.json on 2026-10-28: a lat/lon query
already filters to entities whose geometry contains the point, so no client-side WKT parsing
is needed. `listed-building-outline` (a polygon dataset) is queried in place of the spec's
25m `listed-building` point-radius special case - both give the same practical coverage, and
it avoids a second query shape (scope call).

Heat-pump rule **verified** 2026-10-28: the Town and Country Planning (General Permitted
Development) (England) (Amendment) Order 2025 (S.I. 2025/560, in force 29 May 2025) removed the
1 m boundary-distance restriction for air source heat pumps in England; noise compliance via the
MCS 020 sound calculation has been mandatory since 20 September 2025. Listed buildings, flats and
conservation-area wall-fronting-highway placements are still restricted (spec's own rules below)."""

PLANNING_DATA_BASE = "https://www.planning.data.gov.uk"
ITEMS_LIMIT = 5

DATASETS: dict[str, str] = {
    "conservation-area": "Conservation area",
    "article-4-direction-area": "Article 4 direction",
    "listed-building-outline": "Listed building",
    "tree-preservation-zone": "Tree preservation order/zone",
    "world-heritage-site": "World Heritage Site",
    "area-of-outstanding-natural-beauty": "Area of Outstanding Natural Beauty",
    "national-park": "National Park",
}
CACHE_DAYS = 30

# {family: (keywords matched against measure id/name, lowercased)}
MEASURE_FAMILY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("windows", ("glaz", "window", "shutter", "awning")),
    ("doors", ("door", "air-brick")),
    ("roofing", ("roof", "loft")),
    ("solar", ("solar", "pv", "photovoltaic")),
    ("heat_pump", ("heat pump", "heat-pump", "ashp")),
    ("wall_insulation", ("wall", "cladding", "render", "insulat")),
    ("tree_works", ("tree",)),
    ("hard_surfacing", ("paving", "driveway", "drain", "permeable")),
]
DEFAULT_FAMILY = "other"

PLANNING_PORTAL_URL = "https://www.planningportal.co.uk/permission/common-projects"
GPDO_URL = "https://www.legislation.gov.uk/uksi/2015/596/schedule/2"
FIND_COUNCIL_URL = "https://www.gov.uk/find-local-council"

DISCLAIMER = "Indicative only, not legal advice. Check with your council before work starts."
