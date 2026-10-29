"""Compare config (docs/studio/N_20_function.md §S18). No new external source: this feature
only re-runs N's existing adapters, L's `assess_risk`/`compute_score`, and N's planner,
read-only, on addresses that are not saved as homes."""

from datetime import timedelta

MIN_CANDIDATES = 2
MAX_CANDIDATES = 3

RATE_LIMIT_COMPARE = (10, timedelta(hours=1))  # per user

TOP_MEASURES_LIMIT = 3
SCORE_TARGET = 70

LABELS = ("A", "B", "C")

NEUTRAL_HOUSEHOLD = {
    "tenure": "owner_occupier",
    "income_band": "40k_60k",
    "budget_gbp": 0,
    "priorities": [],
    "vulnerable": None,
}
