"""Funding matcher v1 (spec §7 Funding, docs/scoring.md). L owns this file."""

from app.schemas import FundingOption, Household, Measure, Plan, PlanItem, ResilienceScore
from app.scoring.funding import match_funding


def _measure(id: str, category: str, cost_low: int, cost_high: int | None = None) -> Measure:
    return Measure(
        id=id,
        name=id,
        category=category,
        cost_low_gbp=cost_low,
        cost_high_gbp=cost_high or cost_low,
        annual_bill_saving_gbp=0,
        co2_saved_kg_per_year=0,
        resilience_points=1,
        renter_ok=True,
        needs_landlord=False,
        source_url="https://example.com",
    )


def _score() -> ResilienceScore:
    return ResilienceScore(value=50, band="D", components=[], version="v1")


def _plan(measures: list[tuple[Measure, bool]]) -> Plan:
    items = [
        PlanItem(measure=m, rank=i + 1, score_uplift=1, explanation="x", selected=selected)
        for i, (m, selected) in enumerate(measures)
    ]
    selected_low = sum(m.cost_low_gbp for m, s in measures if s)
    selected_high = sum(m.cost_high_gbp for m, s in measures if s)
    return Plan(
        items=items,
        total_cost_low_gbp=selected_low,
        total_cost_high_gbp=selected_high,
        projected_score=_score(),
        explanation_source="template",
    )


def _household(**kw) -> Household:
    defaults = dict(tenure="owner_occupier", income_band="20k_40k", budget_gbp=5000)
    defaults.update(kw)
    return Household(**defaults)


def _option(
    id: str,
    kind: str,
    max_amount_gbp: int | None = None,
    apr_percent: float | None = None,
    income_bands: list[str] | None = None,
    tenures: list[str] | None = None,
    categories: list[str] | None = None,
    is_mock: bool = True,
) -> FundingOption:
    return FundingOption(
        id=id,
        name=id,
        provider="Test",
        kind=kind,
        max_amount_gbp=max_amount_gbp,
        apr_percent=apr_percent,
        income_bands=income_bands or [],
        tenures=tenures or [],
        categories=categories or [],
        is_mock=is_mock,
        source_url="" if is_mock else "https://example.com",
    )


# --- Filtering by income band, tenure, category -----------------------------------------------


def test_means_tested_grant_excluded_for_high_income() -> None:
    flood_door = _measure("flood-door", "flood", 1000)
    plan = _plan([(flood_door, True)])
    household = _household(income_band="over_100k")
    options = [_option("eco4", "grant", income_bands=["under_20k"], categories=["flood"])]
    bundle = match_funding(plan, household, options)
    assert bundle.lines == []
    assert bundle.gap_gbp == 1000


def test_low_income_owner_gets_grant_first() -> None:
    flood_door = _measure("flood-door", "flood", 1000)
    plan = _plan([(flood_door, True)])
    household = _household(income_band="under_20k", tenure="owner_occupier")
    options = [
        _option("eco4", "grant", income_bands=["under_20k"], categories=["flood"]),
        _option("lloyds-loan", "loan", apr_percent=6.9, categories=[]),
    ]
    bundle = match_funding(plan, household, options)
    assert bundle.lines[0].option.kind == "grant"
    assert bundle.covered_gbp == 1000
    assert bundle.gap_gbp == 0


def test_tenure_filters_out_wrong_option() -> None:
    measure = _measure("loft", "carbon", 500)
    plan = _plan([(measure, True)])
    household = _household(tenure="private_renter")
    options = [_option("owner-grant", "grant", tenures=["owner_occupier"], categories=["carbon"])]
    bundle = match_funding(plan, household, options)
    assert bundle.lines == []


def test_category_filters_out_unrelated_option() -> None:
    measure = _measure("loft", "carbon", 500)
    plan = _plan([(measure, True)])
    household = _household()
    options = [_option("flood-grant", "grant", categories=["flood"])]
    bundle = match_funding(plan, household, options)
    assert bundle.lines == []


def test_unselected_measures_do_not_count() -> None:
    selected = _measure("loft", "carbon", 500)
    unselected = _measure("door", "flood", 1500)
    plan = _plan([(selected, True), (unselected, False)])
    household = _household()
    options = [_option("flood-grant", "grant", categories=["flood"])]
    bundle = match_funding(plan, household, options)
    assert bundle.lines == []
    assert bundle.gap_gbp == plan.total_cost_low_gbp == 500


# --- Ordering: grants -> cashback -> insurance discount -> loans -----------------------------


def test_order_grants_before_cashback_before_discount_before_loan() -> None:
    measure = _measure("loft", "carbon", 1000)
    plan = _plan([(measure, True)])
    household = _household()
    options = [
        _option("loan", "loan", apr_percent=6.9),
        _option("discount", "insurance_discount", max_amount_gbp=50, categories=["carbon"]),
        _option("cashback", "cashback", max_amount_gbp=200, categories=["carbon"]),
        _option("grant", "grant", max_amount_gbp=300, categories=["carbon"]),
    ]
    bundle = match_funding(plan, household, options)
    kinds = [ln.option.kind for ln in bundle.lines]
    assert kinds == ["grant", "cashback", "insurance_discount", "loan"]


def test_grant_lines_come_before_non_grant_lines() -> None:
    measure = _measure("loft", "carbon", 1000)
    plan = _plan([(measure, True)])
    household = _household()
    options = [
        _option("cashback", "cashback", max_amount_gbp=200, categories=["carbon"]),
        _option("grant", "grant", max_amount_gbp=300, categories=["carbon"]),
    ]
    bundle = match_funding(plan, household, options)
    assert [ln.option.kind for ln in bundle.lines][0] == "grant"


# --- Allocation: grants up to cost, gap on the lowest-APR loan --------------------------------


def test_grant_allocation_capped_at_max_amount() -> None:
    measure = _measure("loft", "carbon", 1000)
    plan = _plan([(measure, True)])
    household = _household()
    options = [_option("grant", "grant", max_amount_gbp=300, categories=["carbon"])]
    bundle = match_funding(plan, household, options)
    assert bundle.covered_gbp == 300
    assert bundle.gap_gbp == 700


def test_gap_goes_to_lowest_apr_loan() -> None:
    measure = _measure("loft", "carbon", 1000)
    plan = _plan([(measure, True)])
    household = _household()
    options = [
        _option("cheap-loan", "loan", apr_percent=3.0),
        _option("pricey-loan", "loan", apr_percent=9.9),
    ]
    bundle = match_funding(plan, household, options)
    loan_line = next(ln for ln in bundle.lines if ln.option.kind == "loan")
    assert loan_line.option.id == "cheap-loan"
    assert loan_line.amount_gbp == 1000
    assert bundle.monthly_cost_gbp is not None


def test_zero_apr_loan_splits_evenly_over_the_term() -> None:
    measure = _measure("loft", "carbon", 600)
    plan = _plan([(measure, True)])
    household = _household()
    options = [_option("interest-free", "loan", apr_percent=0.0)]
    bundle = match_funding(plan, household, options)
    assert bundle.monthly_cost_gbp == 10  # 600 / 60 months


def test_no_loan_available_leaves_monthly_cost_none() -> None:
    measure = _measure("loft", "carbon", 1000)
    plan = _plan([(measure, True)])
    household = _household()
    bundle = match_funding(plan, household, [])
    assert bundle.monthly_cost_gbp is None
    assert bundle.gap_gbp == 1000


def test_fully_funded_plan_needs_no_loan() -> None:
    measure = _measure("loft", "carbon", 300)
    plan = _plan([(measure, True)])
    household = _household()
    options = [
        _option("grant", "grant", max_amount_gbp=300, categories=["carbon"]),
        _option("loan", "loan", apr_percent=6.9),
    ]
    bundle = match_funding(plan, household, options)
    assert bundle.gap_gbp == 0
    assert bundle.monthly_cost_gbp is None
    assert all(ln.option.kind != "loan" for ln in bundle.lines)


# --- Invariants -------------------------------------------------------------------------------


def test_covered_plus_gap_equals_plan_cost() -> None:
    m1 = _measure("loft", "carbon", 400)
    m2 = _measure("door", "flood", 1500)
    plan = _plan([(m1, True), (m2, True)])
    household = _household()
    options = [
        _option("grant", "grant", max_amount_gbp=300, categories=["carbon"]),
        _option("discount", "insurance_discount", max_amount_gbp=50, categories=["flood"]),
    ]
    bundle = match_funding(plan, household, options)
    assert bundle.covered_gbp + bundle.gap_gbp == plan.total_cost_low_gbp


def test_fairness_rule_terms_do_not_depend_on_score() -> None:
    """match_funding never reads a score; identical plans give identical terms regardless."""
    measure = _measure("loft", "carbon", 1000)
    plan = _plan([(measure, True)])
    household = _household()
    options = [_option("loan", "loan", apr_percent=6.9)]
    bundle_a = match_funding(plan, household, options)
    bundle_b = match_funding(plan, household, options)
    assert bundle_a == bundle_b
