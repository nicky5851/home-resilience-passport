"""Scoring interface (spec §4.3). L owns this package; N calls only these names.

All functions are pure: no network, no database, deterministic. Every threshold and weight
lives in `app/scoring/config.py`.
"""

from app.scoring.config import SCORING_VERSION
from app.scoring.funding import match_funding
from app.scoring.risk import assess_risk
from app.scoring.score import compute_score

__all__ = ["SCORING_VERSION", "assess_risk", "compute_score", "match_funding"]
