"""Mounts every feature under `/api/v1/studio` by discovering `app.studio.features.*`
(docs/studio/N_20_function.md §3 step 2). Also serves the hub's own two routes."""

import importlib
import pkgutil

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.config import get_settings
from app.studio import features as features_pkg
from app.studio.common.home_ref import MaybeUser, resolve_home, summarize
from app.studio.common.schemas import FeatureMeta, StudioHomeSummary

router = APIRouter(prefix="/studio", tags=["studio"])

_metas: list[FeatureMeta] = []


def _discover() -> None:
    disabled = get_settings().studio_disabled_ids
    names = sorted(m.name for m in pkgutil.iter_modules(features_pkg.__path__))
    for name in names:
        pkg_name = f"{features_pkg.__name__}.{name}"
        meta_mod = importlib.import_module(f"{pkg_name}.meta")
        meta: FeatureMeta = meta_mod.META
        if meta.id in disabled:
            continue
        router_mod = importlib.import_module(f"{pkg_name}.router")
        router.include_router(router_mod.router)
        _metas.append(meta)


_discover()


def feature_metas() -> list[FeatureMeta]:
    return list(_metas)


@router.get("/features")
def list_features() -> list[FeatureMeta]:
    return feature_metas()


@router.get("/homes/{ref}")
async def home_summary(ref: str, session: SessionDep, user: MaybeUser) -> StudioHomeSummary:
    home = await resolve_home(ref, session, user)
    return summarize(home)
