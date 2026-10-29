from datetime import UTC, datetime

from fastapi import APIRouter, Query

from app.adapters import postcodes
from app.adapters.http import UpstreamUnavailable
from app.api.deps import ApiCacheDep, CurrentUser, SessionDep, rate_limit
from app.api.errors import ApiError
from app.api.lookup import SUPPORTED_COUNTRIES, UNSUPPORTED_REGION_DETAIL
from app.api.stub_store import fixture_by_postcode, fixtures
from app.schemas import Address, Household
from app.schemas.hazards import RiskProfile
from app.schemas.plan import Measure
from app.schemas.property import PropertyFacts
from app.scoring import compute_score
from app.services import assessment, planner
from app.studio.common.schemas import Evidence
from app.studio.features.s18_home_compare.config import (
    LABELS,
    MAX_CANDIDATES,
    MIN_CANDIDATES,
    NEUTRAL_HOUSEHOLD,
    RATE_LIMIT_COMPARE,
)
from app.studio.features.s18_home_compare.schemas import (
    Candidate,
    Compare,
    CompareHome,
    CompareRequest,
    Winners,
)
from app.studio.features.s18_home_compare.service import (
    cost_to_70,
    overall_winner,
    top_measures,
    winner_for_component,
)

router = APIRouter(tags=["studio:s18"])

COMPONENTS = ("flood", "heat", "storm", "subsidence", "carbon")


def _validate_count(n: int) -> None:
    if not (MIN_CANDIDATES <= n <= MAX_CANDIDATES):
        raise ApiError(
            400, "validation", f"Compare {MIN_CANDIDATES} to {MAX_CANDIDATES} homes at a time."
        )


def _household() -> Household:
    return Household.model_validate(NEUTRAL_HOUSEHOLD)


def _build_compare_home(
    label: str,
    line1: str,
    postcode: str,
    prop: PropertyFacts,
    risk: RiskProfile,
    measures: list[Measure],
) -> CompareHome:
    household = _household()
    score = compute_score(risk, prop, [])
    ranked = planner.rank(measures, risk, prop, household, completed=[])
    low, high = cost_to_70(ranked, risk, prop)
    return CompareHome(
        label=label,  # type: ignore[arg-type]
        line1=line1,
        postcode=postcode,
        property=prop,
        risk=risk,
        score=score,
        top_measures=top_measures(ranked),
        cost_to_70_low_gbp=low,
        cost_to_70_high_gbp=high,
    )


def _winners(homes: list[CompareHome]) -> Winners:
    scores = [h.score for h in homes]
    labels = list(LABELS[: len(homes)])
    costs_low = [h.cost_to_70_low_gbp for h in homes]
    kwargs = {name: winner_for_component(scores, labels, name) for name in COMPONENTS}
    kwargs["overall"] = overall_winner(scores, costs_low, labels)
    return Winners(**kwargs)


def _summary(homes: list[CompareHome], winners: Winners) -> str:
    winner_home = next(h for h in homes if h.label == winners.overall)
    others = [h for h in homes if h.label != winners.overall]
    cheapest_other = min(
        (h.cost_to_70_low_gbp for h in others if h.cost_to_70_low_gbp is not None), default=None
    )
    if winner_home.cost_to_70_low_gbp is not None and cheapest_other is not None:
        diff = cheapest_other - winner_home.cost_to_70_low_gbp
        if diff > 0:
            return f"Home {winner_home.label} is £{diff:,} cheaper to make resilient."
    return f"Home {winner_home.label} scores best overall."


async def _resolve_address(candidate: Candidate, cache: ApiCacheDep) -> Address:
    try:
        info = await postcodes.lookup_postcode(candidate.postcode, cache)
    except postcodes.PostcodeNotFound as e:
        raise ApiError(400, "validation", "We couldn't find that postcode.") from e
    except UpstreamUnavailable as e:
        demo = fixture_by_postcode(candidate.postcode)
        if demo is None:
            raise ApiError(502, "upstream_unavailable") from e
        info = postcodes.PostcodeInfo(
            postcode=demo.demo.address.postcode,
            lat=demo.demo.address.lat,
            lon=demo.demo.address.lon,
            local_authority=demo.demo.address.local_authority,
            country=demo.demo.address.country,
        )
    if info.country not in SUPPORTED_COUNTRIES:
        raise ApiError(400, "unsupported_region", UNSUPPORTED_REGION_DETAIL)
    return Address(
        uprn=candidate.uprn,
        line1=candidate.line1,
        postcode=candidate.postcode,
        lat=info.lat,
        lon=info.lon,
        local_authority=info.local_authority,
        country=info.country,
    )


@router.post("/compare")
async def compare(
    body: CompareRequest, user: CurrentUser, session: SessionDep, cache: ApiCacheDep
) -> Compare:
    _validate_count(len(body.candidates))
    rate_limit("studio_compare", str(user.id), RATE_LIMIT_COMPARE)

    measures = await planner.load_measures(session)
    homes: list[CompareHome] = []
    for i, candidate in enumerate(body.candidates):
        address = await _resolve_address(candidate, cache)
        prop = await assessment.property_for(address, None, cache)
        if prop is None:
            prop = PropertyFacts(property_type="semi_detached", source="model")
        result = await assessment.assess(address, prop, session, cache)
        homes.append(
            _build_compare_home(
                LABELS[i], candidate.line1, candidate.postcode, prop, result.risk, measures
            )
        )

    winners = _winners(homes)
    return Compare(
        homes=homes,
        winners=winners,
        summary=_summary(homes, winners),
        evidence=[
            Evidence(
                label="Hazard and EPC data",
                evidence="official_modelled",
                source="Environment Agency, EPC register, Open-Meteo",
                source_url="https://www.gov.uk/check-flooding",
                retrieved_at=datetime.now(UTC),
            )
        ],
        fallback_used=False,
    )


@router.get("/compare/demo")
async def compare_demo(session: SessionDep, slugs: str = Query(...)) -> Compare:
    slug_list = [s.strip() for s in slugs.split(",") if s.strip()]
    _validate_count(len(slug_list))

    all_fixtures = fixtures()
    for slug in slug_list:
        if slug not in all_fixtures:
            raise ApiError(400, "validation", f"Unknown demo home: {slug}.")

    measures = await planner.load_measures(session)
    homes = [
        _build_compare_home(
            LABELS[i],
            all_fixtures[slug].demo.address.line1,
            all_fixtures[slug].demo.address.postcode,
            all_fixtures[slug].demo.property,
            all_fixtures[slug].demo.risk,
            measures,
        )
        for i, slug in enumerate(slug_list)
    ]

    winners = _winners(homes)
    return Compare(
        homes=homes,
        winners=winners,
        summary=_summary(homes, winners),
        evidence=[
            Evidence(
                label="Demo fixture data",
                evidence="estimated",
                source="Home Resilience Passport demo homes",
                source_url="https://www.gov.uk/check-flooding",
                retrieved_at=datetime.now(UTC),
            )
        ],
        fallback_used=False,
    )
