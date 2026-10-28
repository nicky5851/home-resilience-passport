from app.schemas.base import Contract
from app.studio.common.schemas import Evidence


class BandCount(Contract):
    band: str
    count: int


class UpgradeRow(Contract):
    label: str
    share_pct: int
    median_sap_gain: int | None


class Story(Contract):
    distance_m: int
    from_band: str
    to_band: str
    from_sap: int
    to_sap: int
    year_from: int
    year_to: int
    upgrades: list[str]


class StreetProof(Contract):
    peer_definition: str
    peers_count: int
    band_distribution: list[BandCount]
    your_sap: int | None
    your_percentile: int | None
    improvers_count: int
    median_sap_gain: int | None
    top_upgrades: list[UpgradeRow]
    stories: list[Story]
    partial: bool
    evidence: list[Evidence]
    fallback_used: bool
