"""The passport (spec step N14): the home's record, its score with work done, and history.

The score history is the events' `score_after`. Recorded work counts at once: the current
score is L's `compute_score` of the latest risk with every completed measure, so it rises
when work is recorded and stays when the home is assessed again.
"""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.stub_store import StubHome, store
from app.schemas import Measure, Passport, ResilienceScore
from app.scoring import compute_score
from app.services import homes, planner


async def measures_for(session: AsyncSession, home: StubHome) -> list[Measure]:
    """Measures work can be recorded for: the catalogue, or a demo home's fixture plan."""
    if home.stored:
        return await planner.load_measures(session)
    return [i.measure for i in store.plan(home).items]


def completed(
    home: StubHome, measures: Sequence[Measure], extra: str | None = None
) -> list[Measure]:
    """Measures the passport records as done (work_recorded events), plus `extra`."""
    done = {e.detail.get("measure_id") for e in home.events if e.kind == "work_recorded"}
    if extra is not None:
        done.add(extra)
    return [m for m in measures if m.id in done]


def score(home: StubHome, measures: Sequence[Measure], extra: str | None = None) -> ResilienceScore:
    """The latest assessment's score with completed work (and `extra`) counted."""
    done = completed(home, measures, extra)
    a = store.latest_assessment(home)
    if not done:
        return a.score  # a demo home keeps its fixture score until work is recorded
    return compute_score(a.risk, a.inputs.property, done)


async def build(session: AsyncSession, home: StubHome) -> Passport | None:
    """Everything about the home; None for a stored home that has not been assessed yet."""
    measures = await measures_for(session, home)
    if not home.stored:
        p = store.passport(home)
        return p.model_copy(update={"latest_score": score(home, measures)})
    if home.assessment is None or home.real is None:
        return None
    return Passport(
        home_id=home.home_id,
        address=home.real["address"],
        property=home.assessment.inputs.property,  # with our model's estimate, if any (N13)
        household=home.real["household"],
        latest_risk=home.assessment.risk,
        latest_score=score(home, measures),
        plan=await homes.latest_plan(session, home.home_id),
        events=home.events,
        share_token=home.share_token,
    )
