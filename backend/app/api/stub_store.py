"""The five demo homes (spec N3): answered from the fixtures, state kept in memory.

Users' own homes live in Postgres since N10 (`app/services/homes.py`), shown to the routes as
`StubHome` views. Plans and funding still come from the fixtures until N11 / L6. Demo-home
events and share links here are lost when the API restarts.
"""

import json
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from app.config import SHARE_TOKEN_BYTES
from app.schemas import (
    DemoHome,
    FundingBundle,
    HazardInputs,
    Passport,
    PassportEvent,
    Plan,
    ResilienceScore,
    RiskProfile,
)
from app.schemas.api import Assessment

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "demo_homes"
DEFAULT_SLUG = "flood-terrace"


@dataclass
class Fixture:
    slug: str
    demo: DemoHome
    inputs: HazardInputs
    passport: Passport

    @property
    def assessment(self) -> Assessment:
        return Assessment(risk=self.demo.risk, score=self.demo.score, inputs=self.inputs)


@lru_cache
def fixtures() -> dict[str, Fixture]:
    out: dict[str, Fixture] = {}
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        raw = json.loads(path.read_text())
        demo = DemoHome.model_validate({k: raw[k] for k in DemoHome.model_fields})
        out[demo.slug] = Fixture(
            slug=demo.slug,
            demo=demo,
            inputs=HazardInputs.model_validate(raw["inputs"]),
            passport=Passport.model_validate(raw["passport"]),
        )
    return out


def fixture_by_postcode(postcode: str) -> Fixture | None:
    return next((f for f in fixtures().values() if f.demo.address.postcode == postcode), None)


@dataclass
class StubHome:
    home_id: uuid.UUID
    owner: str | None  # user id of a stored home; None = demo home any logged-in user can open
    slug: str
    line1: str
    postcode: str
    assessed: bool = False
    # N9: the real latest assessment for homes stored in the database (None = use the fixture).
    assessment: Assessment | None = None
    # A stored home's address, property and household for its passport.
    real: dict | None = None
    stored: bool = False  # True: a view of a Postgres home (N10); changes go through the service
    share_token: str | None = None
    events: list[PassportEvent] = field(default_factory=list)
    certificates: dict[uuid.UUID, tuple[bytes, str]] = field(default_factory=dict)

    @property
    def fixture(self) -> Fixture:
        return fixtures()[self.slug]


class StubStore:
    def __init__(self) -> None:
        self.homes: dict[uuid.UUID, StubHome] = {}
        for f in fixtures().values():
            self.homes[f.passport.home_id] = StubHome(
                home_id=f.passport.home_id,
                owner=None,
                slug=f.slug,
                line1=f.demo.address.line1,
                postcode=f.demo.address.postcode,
                assessed=True,
                events=list(f.passport.events),
            )

    def get(self, home_id: uuid.UUID) -> StubHome | None:
        """A demo home; users' own homes are in Postgres."""
        return self.homes.get(home_id)

    def by_share_token(self, token: str) -> StubHome | None:
        return next((h for h in self.homes.values() if h.share_token == token), None)

    def assess(self, home: StubHome) -> Assessment:
        home.assessed = True
        a = home.fixture.assessment
        home.events.append(
            PassportEvent(
                id=uuid.uuid4(), kind="assessed", at=now(), score_after=a.score.value, detail={}
            )
        )
        return a

    def share(self, home: StubHome) -> str:
        home.share_token = secrets.token_urlsafe(SHARE_TOKEN_BYTES)
        home.events.append(
            PassportEvent(id=uuid.uuid4(), kind="shared", at=now(), score_after=None, detail={})
        )
        return home.share_token

    def passport(self, home: StubHome) -> Passport:
        f = home.fixture
        risk, score = self.latest(home)
        update = {
            "home_id": home.home_id,
            "address": f.demo.address.model_copy(update={"line1": home.line1}),
            "latest_risk": risk,
            "latest_score": score,
            "events": home.events,
            "share_token": home.share_token,
        }
        if home.real is not None:  # N9: a database home's own address, property and household
            update |= home.real
        return f.passport.model_copy(update=update)

    def plan(self, home: StubHome) -> Plan:
        return home.fixture.demo.plan

    def funding(self, home: StubHome) -> FundingBundle:
        return home.fixture.demo.funding

    def latest(self, home: StubHome) -> tuple[RiskProfile, ResilienceScore]:
        if home.assessment is not None:
            return home.assessment.risk, home.assessment.score
        return home.fixture.demo.risk, home.fixture.demo.score

    def latest_assessment(self, home: StubHome) -> Assessment:
        return home.assessment or home.fixture.assessment


def now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


store = StubStore()
