"""Funding bundle for a plan. L3 stub: no lines, the whole cost is the gap; real rules in L6."""

from collections.abc import Sequence

from app.schemas import FundingBundle, FundingOption, Household, Plan


def match_funding(
    plan: Plan, household: Household, options: Sequence[FundingOption]
) -> FundingBundle:
    return FundingBundle(
        lines=[], covered_gbp=0, gap_gbp=plan.total_cost_low_gbp, monthly_cost_gbp=None
    )
