from fastapi import APIRouter

from app.studio.features.s20_portfolio.data import load
from app.studio.features.s20_portfolio.schemas import Portfolio, ScenarioRequest, ScenarioResult
from app.studio.features.s20_portfolio.service import build_portfolio, run_scenario

router = APIRouter(prefix="/portfolio", tags=["studio:s20"])


@router.get("")
def portfolio() -> Portfolio:
    return build_portfolio(load())


@router.post("/scenario")
def scenario(body: ScenarioRequest) -> ScenarioResult:
    return run_scenario(load(), body.uptake_pct, body.by_year)
