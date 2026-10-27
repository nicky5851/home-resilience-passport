"""N8 hand-off: `make fixtures` recomputes outputs from inputs with L's scoring."""

import copy

from app.schemas import DemoHome, HazardInputs
from app.scoring import assess_risk
from scripts.make_fixtures import refresh_outputs


def test_refresh_outputs_matches_scoring(demo_fixture: dict) -> None:
    fixture = refresh_outputs(copy.deepcopy(demo_fixture))
    expected = assess_risk(HazardInputs.model_validate(fixture["inputs"]))
    assert fixture["risk"] == expected.model_dump(mode="json")
    assert fixture["passport"]["latest_risk"] == fixture["risk"]
    assert fixture["passport"]["latest_score"] == fixture["score"]
    DemoHome.model_validate({k: fixture[k] for k in DemoHome.model_fields})


def test_refresh_outputs_keeps_inputs(demo_fixture: dict) -> None:
    fixture = refresh_outputs(copy.deepcopy(demo_fixture))
    for part in ("address", "household", "property", "inputs", "plan", "funding"):
        assert fixture[part] == demo_fixture[part]
