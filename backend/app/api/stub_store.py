"""Foundation stub (spec N3): answers from the demo fixtures and keeps state in memory.

Replaced piece by piece by the real services (N4 database, N9 assessment, N10 auth, N11 planner,
N14 passport). Everything here is lost when the API restarts.
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
STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")  # CONTRACT §4
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
    owner: str | None  # email; None = demo home any logged-in user can open
    slug: str
    line1: str
    postcode: str
    assessed: bool = False
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

    def create_home(self, owner: str, line1: str, postcode: str) -> StubHome:
        match = fixture_by_postcode(postcode)
        home = StubHome(
            home_id=uuid.uuid4(),
            owner=owner,
            slug=match.slug if match else DEFAULT_SLUG,
            line1=line1,
            postcode=postcode,
        )
        self.homes[home.home_id] = home
        return home

    def get(self, home_id: uuid.UUID, user: str) -> StubHome | None:
        home = self.homes.get(home_id)
        if home is None or (home.owner is not None and home.owner != user):
            return None
        return home

    def owned_by(self, user: str) -> list[StubHome]:
        return [h for h in self.homes.values() if h.owner == user]

    def delete_user(self, user: str) -> None:
        for home in self.owned_by(user):
            del self.homes[home.home_id]

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
        return f.passport.model_copy(
            update={
                "home_id": home.home_id,
                "address": f.demo.address.model_copy(update={"line1": home.line1}),
                "events": home.events,
                "share_token": home.share_token,
            }
        )

    def plan(self, home: StubHome) -> Plan:
        return home.fixture.demo.plan

    def funding(self, home: StubHome) -> FundingBundle:
        return home.fixture.demo.funding

    def latest(self, home: StubHome) -> tuple[RiskProfile, ResilienceScore]:
        return home.fixture.demo.risk, home.fixture.demo.score


def now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


store = StubStore()
