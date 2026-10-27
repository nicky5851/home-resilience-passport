import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "demo_homes"
DEMO_SLUGS = ("flood-terrace", "coastal-bungalow", "city-top-flat", "clay-semi", "rural-cottage")


def load_fixture(slug: str) -> dict:
    return json.loads((FIXTURES_DIR / f"{slug}.json").read_text())


@pytest.fixture(params=DEMO_SLUGS)
def demo_fixture(request: pytest.FixtureRequest) -> dict:
    return load_fixture(request.param)
