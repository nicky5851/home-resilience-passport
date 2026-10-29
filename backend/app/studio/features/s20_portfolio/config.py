"""Portfolio config (docs/studio/N_20_function.md §S20). The sample itself is built offline
by `scripts/build_studio_portfolio.py` (`make studio-portfolio`) and read from
`backend/app/studio/data/portfolio_sample.json`; this feature's route never calls out."""

from pathlib import Path

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "portfolio_sample.json"

MIN_HOMES_PER_DISTRICT = 5
ATTRIBUTION_FACTOR = 0.6  # illustrative loan-to-value, PCAF-style attribution (verify, §8)

SAMPLE_NOTE = (
    "500 real, anonymised EPC certificates sampled from the public register across three "
    "English regions. No address, house number or UPRN is used or stored; see the EPC "
    "data licensing page for non-address fields."
)
ATTRIBUTION_NOTE = (
    "Financed emissions use an illustrative attribution factor of 60% (a stand-in loan-to-"
    "value), following the PCAF method for mortgages. This is for illustration only, not a "
    "real loan book."
)
FAIRNESS_NOTE = "Scores are never used to raise prices or rates."

EVIDENCE_SOURCE = "EPC register (public, OGL), Environment Agency RoFRS, Open-Meteo climate"
EVIDENCE_URL = "https://get-energy-performance-data.communities.gov.uk/"

MIN_UPTAKE_PCT = 0
MAX_UPTAKE_PCT = 100
MIN_SCENARIO_YEAR = 2026
MAX_SCENARIO_YEAR = 2035
