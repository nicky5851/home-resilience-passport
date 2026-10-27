from typing import Literal

from app.schemas.base import Contract, ShortText


class FundingOption(Contract):
    """One row of data/reference/funding.csv (CONTRACT §5)."""

    id: str
    name: str
    provider: str
    kind: Literal["grant", "loan", "mortgage_further_advance", "insurance_discount", "cashback"]
    max_amount_gbp: int | None = None  # None = no cap
    apr_percent: float | None = None  # loans only
    income_bands: list[str] = []  # empty = all
    tenures: list[str] = []  # empty = all
    categories: list[str] = []  # empty = all
    is_mock: bool
    source_url: str  # may be "" when is_mock


class FundingLine(Contract):
    option: FundingOption
    amount_gbp: int
    note: ShortText


class FundingBundle(Contract):
    lines: list[FundingLine] = []  # grants first
    covered_gbp: int
    gap_gbp: int
    monthly_cost_gbp: int | None = None
