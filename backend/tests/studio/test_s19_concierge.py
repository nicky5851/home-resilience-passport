"""S19: no personal data ever reaches a tool output or prompt, the number guard, the postcode
scrubber, template answers for all 8 intents with no key, and the rate limit."""

from types import SimpleNamespace

import pytest
from anthropic.types import TextBlock, ToolUseBlock

from app.config import get_settings
from app.services import llm, planner
from app.studio.common.home_ref import resolve_home
from app.studio.features.s19_concierge.guard import extract_numbers, numbers_supported
from app.studio.features.s19_concierge.scrub import scrub_personal
from app.studio.features.s19_concierge.template import detect_intent
from app.studio.features.s19_concierge.tools import TOOL_SPECS, ToolContext, call_tool

API = "/api/v1"

PERSONAL_KEYS = {
    "line1",
    "postcode",
    "uprn",
    "local_authority",
    "lat",
    "lon",
    "email",
    "income_band",
    "budget_gbp",
    "tenure",
    "vulnerable",
}


def _keys(value: object) -> set[str]:
    out: set[str] = set()
    if isinstance(value, dict):
        for k, v in value.items():
            out.add(k)
            out |= _keys(v)
    elif isinstance(value, list):
        for item in value:
            out |= _keys(item)
    return out


@pytest.mark.anyio
async def test_concierge_prompt_has_no_personal_data(engine, seeded) -> None:
    from app.db.session import make_sessionmaker

    async with make_sessionmaker(engine)() as session:
        home = await resolve_home("demo-city-top-flat", session, None, include_household=True)
        assert home.household is not None  # the fixture has one; tools must never use it
        measures = await planner.load_measures(session)
        funding = await planner.load_funding_options(session)
    ctx = ToolContext(home=home, measures=measures, funding=funding)

    for spec in TOOL_SPECS:
        args: dict = {"id": "x", "term": "epc", "category": "flood", "kind": "grant"}
        result = call_tool(spec["name"], args, ctx)
        leaked = _keys(result) & PERSONAL_KEYS
        assert not leaked, f"{spec['name']} leaked keys {leaked}"


@pytest.mark.parametrize(
    "answer,outputs,expected",
    [
        ("This costs £500.", '{"cost_low_gbp": 500}', True),
        ("This costs £999.", '{"cost_low_gbp": 500}', False),
        ("No numbers here.", "{}", True),
        ("Saves 12% on bills.", '{"percent": 12}', True),
        ("Saves 99% on bills.", '{"percent": 12}', False),
    ],
)
def test_number_guard(answer, outputs, expected) -> None:
    assert numbers_supported(answer, outputs) is expected


def test_extract_numbers_finds_units() -> None:
    assert extract_numbers("£1,200 and 50% and 10kWh and 5kg and 3 points") == [
        "£1,200",
        "50%",
        "10kWh",
        "5kg",
        "3 points",
    ]


@pytest.mark.parametrize(
    "text,should_be_removed",
    [
        ("my postcode is SW1A 1AA", "SW1A 1AA"),
        ("email me at test@example.com", "test@example.com"),
    ],
)
def test_scrub_personal_removes_postcodes_and_emails(text, should_be_removed) -> None:
    scrubbed = scrub_personal(text)
    assert should_be_removed not in scrubbed
    assert "[removed]" in scrubbed


@pytest.mark.parametrize(
    "message,intent",
    [
        ("What's my biggest risk?", "biggest_risk"),
        ("Why is my score what it is?", "explain_score"),
        ("What's the cheapest way to cut my bills?", "cheapest_bill_saving"),
        ("Tell me about flood risk", "flood"),
        ("Will my home overheat?", "heat"),
        ("Is there any grant funding?", "funding"),
        ("I'm a renter, what can I do?", "renters"),
        ("What should I do next?", "what_next"),
        ("Completely unrelated gibberish", "what_next"),
    ],
)
def test_intent_router_covers_all_eight_intents(message, intent) -> None:
    assert detect_intent(message) == intent


@pytest.mark.parametrize(
    "message",
    [
        "What's my biggest risk?",
        "Why is my score what it is?",
        "What's the cheapest way to cut my bills?",
        "Tell me about flood risk",
        "Will my home overheat?",
        "Is there any grant funding?",
        "I'm a renter, what can I do?",
        "What should I do next?",
    ],
)
def test_template_answers_all_eight_intents_with_no_key(client, monkeypatch, message) -> None:
    monkeypatch.setattr(get_settings(), "anthropic_api_key", None)
    res = client.post(
        f"{API}/studio/homes/demo-flood-terrace/concierge",
        json={"messages": [{"role": "user", "content": message}]},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["source"] == "template"
    assert body["citations"]
    assert body["answer"]


def test_concierge_rate_limited_for_demo_ip(client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "anthropic_api_key", None)
    from app.studio.features.s19_concierge.config import RATE_LIMIT_CONCIERGE_DEMO_IP

    limit = RATE_LIMIT_CONCIERGE_DEMO_IP[0]
    body = {"messages": [{"role": "user", "content": "What's my biggest risk?"}]}
    for _ in range(limit):
        res = client.post(f"{API}/studio/homes/demo-flood-terrace/concierge", json=body)
        assert res.status_code == 200
    res = client.post(f"{API}/studio/homes/demo-flood-terrace/concierge", json=body)
    assert res.status_code == 429


def test_concierge_rejects_non_user_last_message(client) -> None:
    body = {
        "messages": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
    }
    res = client.post(f"{API}/studio/homes/demo-flood-terrace/concierge", json=body)
    assert res.status_code == 400


def test_llm_path_answers_with_citations_and_passes_guard(client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "test-key")
    monkeypatch.setattr(llm, "daily_cap", llm._DailyCap())

    calls = {"n": 0}

    async def fake_tool_call(system, messages, tools):
        calls["n"] += 1
        if calls["n"] == 1:
            return SimpleNamespace(
                stop_reason="tool_use",
                content=[ToolUseBlock(id="t1", name="get_risk_levels", input={}, type="tool_use")],
            )
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[TextBlock(type="text", text="Your flood risk is medium today.")],
        )

    monkeypatch.setattr(llm, "tool_call", fake_tool_call)
    res = client.post(
        f"{API}/studio/homes/demo-flood-terrace/concierge",
        json={"messages": [{"role": "user", "content": "What's my biggest risk?"}]},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["source"] == "llm"
    assert body["citations"] == [{"tool": "get_risk_levels", "label": "This home's hazard levels"}]


def test_llm_path_falls_back_when_guard_fails(client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "test-key")
    monkeypatch.setattr(llm, "daily_cap", llm._DailyCap())

    async def fake_tool_call(system, messages, tools):
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[TextBlock(type="text", text="This measure costs £999,999.")],
        )

    monkeypatch.setattr(llm, "tool_call", fake_tool_call)
    res = client.post(
        f"{API}/studio/homes/demo-flood-terrace/concierge",
        json={"messages": [{"role": "user", "content": "What's my biggest risk?"}]},
    )
    assert res.status_code == 200, res.text
    assert res.json()["source"] == "template"


def test_llm_path_falls_back_when_no_key(client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "anthropic_api_key", None)
    res = client.post(
        f"{API}/studio/homes/demo-flood-terrace/concierge",
        json={"messages": [{"role": "user", "content": "What's my biggest risk?"}]},
    )
    assert res.status_code == 200, res.text
    assert res.json()["source"] == "template"
