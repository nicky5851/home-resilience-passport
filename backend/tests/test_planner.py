"""N11: planner (spec §7) and LLM explanations, offline (the LLM call is always mocked)."""

import asyncio
import json

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.db.reference import REFERENCE_DIR, load_reference
from app.schemas import Household, Measure, Plan, PropertyFacts, ResilienceScore, RiskProfile
from app.scoring import compute_score as real_compute_score
from app.services import llm, planner
from tests.conftest import DEMO_SLUGS, load_fixture

API = "/api/v1"


def _csv_measures() -> list[Measure]:
    return [Measure.model_validate(r) for r in load_reference(REFERENCE_DIR).rows["measures.csv"]]


def _measure(mid: str, **kw) -> Measure:
    base = dict(
        id=mid, name=mid.title(), category="flood", hazards_reduced=["river_sea_flood"],
        cost_low_gbp=100, cost_high_gbp=300, annual_bill_saving_gbp=0, co2_saved_kg_per_year=0,
        resilience_points=5, property_types=[], renter_ok=True, needs_landlord=False,
        source_url="https://example.com",
    )  # fmt: skip
    return Measure.model_validate(base | kw)


def _parts(slug: str = "flood-terrace", **household):
    f = load_fixture(slug)
    return (
        RiskProfile.model_validate(f["risk"]),
        PropertyFacts.model_validate(f["property"]),
        Household.model_validate(f["household"] | household),
    )


@pytest.fixture
def points_score(monkeypatch):
    """Each measure adds its `resilience_points`, so uplifts differ (L's stub gives 0)."""

    def score(risk, prop, completed=()):
        s = real_compute_score(risk, prop)
        return s.model_copy(update={"value": 50 + sum(m.resilience_points for m in completed)})

    monkeypatch.setattr(planner, "compute_score", score)


@pytest.fixture
def no_llm(monkeypatch):
    async def none(facts, session):
        return None

    monkeypatch.setattr(llm, "explanations", none)


def _plan(measures, *parts, completed=(), **kw) -> Plan:
    return asyncio.run(planner.build_plan(None, measures, *parts, list(completed), **kw))


# --- Planner rules (spec §7) -----------------------------------------------------------------


@pytest.mark.parametrize("slug", DEMO_SLUGS)
def test_plan_for_each_demo_home_is_schema_valid(no_llm, slug) -> None:
    plan = _plan(_csv_measures(), *_parts(slug))
    Plan.model_validate(plan.model_dump())
    assert plan.explanation_source == "template"
    assert [i.rank for i in plan.items] == list(range(1, len(plan.items) + 1))


@pytest.mark.parametrize("tenure", ["private_renter", "social_renter"])
def test_renters_get_landlord_measures_only_in_their_own_group(no_llm, tenure) -> None:
    plan = _plan(_csv_measures(), *_parts(tenure=tenure, budget_gbp=100_000))
    landlord = [i.measure.needs_landlord for i in plan.items]
    assert any(landlord) and not all(landlord)
    assert landlord == sorted(landlord)  # main list first, then the landlord group
    assert not any(i.selected for i in plan.items if i.measure.needs_landlord)
    sel = _plan(_csv_measures(), *_parts(tenure=tenure), selected_ids=["flood-door"])
    assert not any(i.selected for i in sel.items)  # cannot be selected either


def test_owners_get_landlord_measures_in_the_main_list(no_llm) -> None:
    plan = _plan(_csv_measures(), *_parts(tenure="owner_occupier", budget_gbp=100_000))
    assert all(i.selected for i in plan.items)


def test_rank_by_uplift_per_pound(points_score, no_llm) -> None:
    ms = [
        _measure("cheap-small", resilience_points=2, cost_low_gbp=10, cost_high_gbp=30),  # 2/50
        _measure(
            "pricey-big", resilience_points=10, cost_low_gbp=900, cost_high_gbp=1100
        ),  # 10/1000
        _measure("mid", resilience_points=6, cost_low_gbp=100, cost_high_gbp=100),  # 6/100
    ]
    plan = _plan(ms, *_parts(priorities=[]))
    assert [i.measure.id for i in plan.items] == ["mid", "cheap-small", "pricey-big"]
    assert [i.score_uplift for i in plan.items] == [6, 2, 10]


def test_priorities_add_20_percent(points_score, no_llm) -> None:
    ms = [
        _measure("flood-a", resilience_points=10, cost_low_gbp=100, cost_high_gbp=100),
        _measure("heat-b", category="heat", resilience_points=9, cost_low_gbp=100,
                 cost_high_gbp=100),
    ]  # fmt: skip
    assert _plan(ms, *_parts(priorities=[])).items[0].measure.id == "flood-a"
    assert _plan(ms, *_parts(priorities=["comfort"])).items[0].measure.id == "heat-b"


@pytest.mark.parametrize(
    ("priority", "matches"),
    [
        ("lower_bills", {"bills"}),
        ("comfort", {"heat"}),
        ("flood_safety", {"flood"}),
        ("lower_carbon", {"carbon"}),
        ("home_value", {"bills", "carbon"}),  # raise the EPC: energy cost or CO2
    ],
)
def test_priority_mapping(priority, matches) -> None:
    ms = {
        "bills": _measure("bills", category="storm", annual_bill_saving_gbp=40),
        "heat": _measure("heat", category="heat"),
        "flood": _measure("flood"),
        "carbon": _measure("carbon", category="storm", co2_saved_kg_per_year=90),
        "none": _measure("none", category="storm"),
    }
    assert {k for k, m in ms.items() if planner.matches_priority(m, [priority])} == matches


def test_vulnerable_households_get_heat_and_flood_first(points_score, no_llm) -> None:
    ms = [
        _measure("storm-a", category="storm", resilience_points=10, cost_low_gbp=10),
        _measure("heat-b", category="heat", resilience_points=1, cost_low_gbp=500),
    ]
    assert _plan(ms, *_parts(vulnerable=None)).items[0].measure.id == "storm-a"
    assert _plan(ms, *_parts(vulnerable=True)).items[0].measure.id == "heat-b"


def test_ties_go_to_lower_cost_then_id(no_llm) -> None:
    ms = [_measure("b", cost_low_gbp=50), _measure("c", cost_low_gbp=10), _measure("a")]
    assert [i.measure.id for i in _plan(ms, *_parts(priorities=[])).items] == ["c", "b", "a"]


def test_property_types_and_completed_measures_filter(no_llm) -> None:
    risk, prop, hh = _parts("city-top-flat")  # a flat
    ms = [_measure("any"), _measure("houses-only", property_types=["detached"]), _measure("done")]
    plan = _plan(ms, risk, prop, hh, completed=[ms[2]])
    assert [i.measure.id for i in plan.items] == ["any"]


def test_default_selection_fits_the_budget(points_score, no_llm) -> None:
    ms = [
        _measure("first", resilience_points=9, cost_low_gbp=300, cost_high_gbp=300),
        _measure("too-big", resilience_points=8, cost_low_gbp=300, cost_high_gbp=500),
        _measure("fits", resilience_points=1, cost_low_gbp=100, cost_high_gbp=100),
    ]
    plan = _plan(ms, *_parts(budget_gbp=450, priorities=[]))
    assert {i.measure.id for i in plan.items if i.selected} == {"first", "fits"}
    assert (plan.total_cost_low_gbp, plan.total_cost_high_gbp) == (400, 400)
    assert plan.projected_score.value == 60
    other = _plan(ms, *_parts(budget_gbp=450, priorities=[]), budget_gbp=0)
    assert not any(i.selected for i in other.items) and other.projected_score.value == 50


def test_selected_ids_replace_the_default(points_score, no_llm) -> None:
    ms = [_measure("a"), _measure("b")]
    plan = _plan(ms, *_parts(budget_gbp=0), selected_ids=["b", "unknown"])
    assert {i.measure.id for i in plan.items if i.selected} == {"b"}


def test_payback_years(no_llm) -> None:
    ms = [_measure("saves", annual_bill_saving_gbp=50), _measure("no-saving")]
    by_id = {i.measure.id: i.payback_years for i in _plan(ms, *_parts()).items}
    assert by_id == {"saves": 4.0, "no-saving": None}  # (100 + 300) / 2 / 50


def test_template_text() -> None:
    r = planner.Ranked(_measure("flood-door", name="Flood door", cost_low_gbp=1500,
                                cost_high_gbp=3500), 8, False)  # fmt: skip
    assert planner.template(r) == (
        "Flood door reduces your river and sea flooding risk and adds about 8 points "
        "for £1,500–£3,500."
    )
    carbon = planner.Ranked(_measure("led", name="LED lighting", category="carbon",
                                     hazards_reduced=[]), 0, False)  # fmt: skip
    assert planner.template(carbon).startswith("LED lighting cuts your home's carbon emissions")


# --- LLM (spec §7 rule 5, CONTRACT §6 rule 2) ------------------------------------------------


def test_llm_prompt_has_no_personal_data() -> None:
    f = load_fixture("city-top-flat")
    risk, prop, _ = _parts("city-top-flat")
    hh = Household.model_validate(f["household"] | {"budget_gbp": 12_345, "vulnerable": True})
    ranked = planner.rank(_csv_measures(), risk, prop, hh, [])
    score = real_compute_score(risk, prop)
    sent = llm.prompt(planner.llm_facts(ranked, risk, prop, score)) + llm.SYSTEM
    a = f["address"]
    personal = [
        "a@example.com", a["line1"], a["postcode"], a["postcode"].replace(" ", ""),
        *(part.strip() for part in a["line1"].split(",")),
        hh.income_band, "12345", "12,345", hh.tenure, "vulnerable",
        "budget", "tenure", "income", "household", "priorities",
        *(p for p in hh.priorities),
    ]  # fmt: skip
    for value in personal:
        assert str(value).lower() not in sent.lower(), value
    assert (
        len(json.loads(llm.prompt(planner.llm_facts(ranked, risk, prop, score)))["measures"]) <= 8
    )


def test_cache_key_ignores_budget_and_selection() -> None:
    risk, prop, hh = _parts()
    score = real_compute_score(risk, prop)
    keys = {
        llm.cache_key(
            planner.llm_facts(planner.rank(_csv_measures(), risk, prop, h, []), risk, prop, score),
            "m",
        )  # fmt: skip
        for h in (hh, hh.model_copy(update={"budget_gbp": 1}))
    }
    assert len(keys) == 1


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ('{"explanations": [{"id": "a", "text": "Keeps water out."}]}', {"a": "Keeps water out."}),
        ('{"explanations": [{"id": "zzz", "text": "Not asked for."}]}', {}),
        ('{"explanations": [{"id": "a", "text": "' + "word " * 31 + '"}]}', {}),
        ("not json", {}),
    ],
)
def test_parse_keeps_only_valid_sentences(answer, expected) -> None:
    assert llm._parse(answer, {"a"}) == expected


# --- API: stored homes ----------------------------------------------------------------------


@pytest.fixture
def fake_claude(monkeypatch):
    """A key is set and the Messages API call is replaced; `calls` counts it."""
    calls: list[str] = []

    async def create(user_prompt: str) -> str:
        calls.append(user_prompt)
        ids = [m["id"] for m in json.loads(user_prompt)["measures"]]
        return json.dumps({"explanations": [{"id": i, "text": f"Helps with {i}."} for i in ids]})

    monkeypatch.setattr(get_settings(), "anthropic_api_key", "test-key")
    monkeypatch.setattr(llm, "_create", create)
    monkeypatch.setattr(llm, "daily_cap", llm._DailyCap())
    return calls


def _assessed_home(client) -> str:
    f = load_fixture("city-top-flat")  # a renter
    body = {"address": f["address"], "household": f["household"], "property_override": None}
    home_id = client.post(f"{API}/homes", json=body).json()["home_id"]
    assert client.post(f"{API}/homes/{home_id}/assess").status_code == 200
    return home_id


def test_plan_without_a_key_uses_the_template(user_client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "anthropic_api_key", None)
    home_id = _assessed_home(user_client)
    res = user_client.post(f"{API}/homes/{home_id}/plan")
    assert res.status_code == 200
    plan = Plan.model_validate(res.json())
    assert plan.explanation_source == "template"
    assert plan.items and not any(
        i.selected for i in plan.items if i.measure.needs_landlord
    )  # renter


def test_moving_the_budget_never_calls_the_llm_again(user_client, fake_claude) -> None:
    home_id = _assessed_home(user_client)
    first = Plan.model_validate(user_client.post(f"{API}/homes/{home_id}/plan").json())
    second = Plan.model_validate(
        user_client.post(f"{API}/homes/{home_id}/plan", json={"budget_gbp": 0}).json()
    )
    third = Plan.model_validate(
        user_client.post(f"{API}/homes/{home_id}/plan", json={"selected_ids": []}).json()
    )
    assert len(fake_claude) == 1
    assert first.explanation_source == second.explanation_source == "llm"
    assert [i.explanation for i in first.items] == [i.explanation for i in third.items]
    assert not any(i.selected for i in second.items)


def test_daily_cap_falls_back_to_the_template(user_client, fake_claude, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "llm_daily_call_limit", 0)
    home_id = _assessed_home(user_client)
    plan = Plan.model_validate(user_client.post(f"{API}/homes/{home_id}/plan").json())
    assert plan.explanation_source == "template" and fake_claude == []


def test_llm_failure_falls_back_to_the_template(user_client, fake_claude, monkeypatch) -> None:
    async def fails(user_prompt: str) -> None:
        return None

    monkeypatch.setattr(llm, "_create", fails)
    home_id = _assessed_home(user_client)
    plan = Plan.model_validate(user_client.post(f"{API}/homes/{home_id}/plan").json())
    assert plan.explanation_source == "template"


def test_plan_needs_an_assessment(user_client) -> None:
    f = load_fixture("flood-terrace")
    body = {"address": f["address"], "household": f["household"], "property_override": None}
    home_id = user_client.post(f"{API}/homes", json=body).json()["home_id"]
    assert user_client.post(f"{API}/homes/{home_id}/plan").status_code == 404


def test_latest_plan_is_saved_and_completed_work_leaves_the_plan(user_client, db_url) -> None:
    home_id = _assessed_home(user_client)
    first = user_client.post(f"{API}/homes/{home_id}/plan").json()
    done = first["items"][0]["measure"]["id"]
    res = user_client.post(
        f"{API}/homes/{home_id}/work", data={"measure_id": done, "completed_on": "2026-10-01"}
    )
    assert res.status_code == 200, res.text
    after = user_client.post(f"{API}/homes/{home_id}/plan", json={"budget_gbp": 50}).json()
    assert done not in [i["measure"]["id"] for i in after["items"]]

    async def saved() -> list:
        eng = create_async_engine(db_url, poolclass=NullPool)
        async with eng.connect() as conn:
            rows = (await conn.execute(text("SELECT budget_gbp FROM plans"))).all()
        await eng.dispose()
        return rows

    assert asyncio.run(saved()) == [(50,)]  # one row per home: the latest


def test_demo_homes_keep_their_fixture_plan(user_client) -> None:
    f = load_fixture("rural-cottage")
    res = user_client.post(f"{API}/homes/{f['passport']['home_id']}/plan")
    assert res.json() == f["plan"]


def test_score_type_is_unchanged() -> None:
    ResilienceScore.model_validate(load_fixture("clay-semi")["score"])
