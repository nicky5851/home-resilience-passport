"""Funding bundle for a plan (spec CODING_SPEC.md §7 Funding, docs/scoring.md).

`match_funding` is a pure function: filters `options` by income band, tenure and the selected
measures' categories, allocates grants -> cashback -> insurance discount up to the plan's cost,
then puts whatever is left on the lowest-APR loan. Fairness rule: nothing here varies price or
rate by score — every option's terms come straight from the input row.
"""

from collections.abc import Sequence

from app.schemas import FundingBundle, FundingLine, FundingOption, Household, Plan
from app.scoring.config import FUNDING_KIND_ORDER, LOAN_TERM_MONTHS

_LOAN_KINDS = ("loan", "mortgage_further_advance")


def _eligible(
    options: Sequence[FundingOption], household: Household, categories: set[str]
) -> list[FundingOption]:
    matches = [
        opt
        for opt in options
        if (not opt.income_bands or household.income_band in opt.income_bands)
        and (not opt.tenures or household.tenure in opt.tenures)
        and (not opt.categories or categories & set(opt.categories))
    ]
    matches.sort(key=lambda o: (FUNDING_KIND_ORDER[o.kind], o.apr_percent or 0, o.id))
    return matches


def _monthly_cost(amount: int, apr_percent: float | None) -> int:
    """Monthly repayment over `LOAN_TERM_MONTHS` (spec §7 rule 3: 5-year term)."""
    rate = (apr_percent or 0) / 100 / 12
    if not rate:
        return round(amount / LOAN_TERM_MONTHS)
    return round(amount * rate / (1 - (1 + rate) ** -LOAN_TERM_MONTHS))


def match_funding(
    plan: Plan, household: Household, options: Sequence[FundingOption]
) -> FundingBundle:
    chosen = [item.measure for item in plan.items if item.selected]
    categories = {measure.category for measure in chosen}
    cost = plan.total_cost_low_gbp

    eligible = _eligible(options, household, categories)

    lines: list[FundingLine] = []
    remaining = cost
    for opt in eligible:
        if opt.kind in _LOAN_KINDS or remaining <= 0:
            continue
        opt_eligible_cost = sum(
            m.cost_low_gbp for m in chosen if not opt.categories or m.category in opt.categories
        )
        amount = min(remaining, opt_eligible_cost, opt.max_amount_gbp or opt_eligible_cost)
        if amount <= 0:
            continue
        remaining -= amount
        note = "Illustrative product." if opt.is_mock else "You appear to qualify."
        lines.append(FundingLine(option=opt, amount_gbp=amount, note=note))

    covered = sum(ln.amount_gbp for ln in lines)
    gap = cost - covered

    monthly_cost_gbp = None
    loans = [opt for opt in eligible if opt.kind in _LOAN_KINDS]
    if gap > 0 and loans:
        loan = min(loans, key=lambda o: o.apr_percent or 0)
        monthly_cost_gbp = _monthly_cost(gap, loan.apr_percent)
        note = (
            "Illustrative loan over 5 years for the remaining cost."
            if loan.is_mock
            else ("A loan over 5 years for the remaining cost.")
        )
        lines.append(FundingLine(option=loan, amount_gbp=gap, note=note))

    return FundingBundle(
        lines=lines, covered_gbp=covered, gap_gbp=gap, monthly_cost_gbp=monthly_cost_gbp
    )
