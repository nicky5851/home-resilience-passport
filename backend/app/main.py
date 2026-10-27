from fastapi import APIRouter, FastAPI

from app.api import auth, homes, lookup, public
from app.api.errors import ERROR_RESPONSES, install_error_handlers
from app.api.origin import origin_check
from app.config import API_PREFIX, get_settings
from app.schemas.api import Health


def create_app() -> FastAPI:
    settings = get_settings()
    docs_on = not settings.is_production
    app = FastAPI(
        title="Home Resilience Passport API",
        version="0.1.0",
        openapi_url=f"{API_PREFIX}/openapi.json" if docs_on else None,
        docs_url="/docs" if docs_on else None,
        redoc_url=None,
    )
    install_error_handlers(app)
    app.middleware("http")(origin_check)

    api = APIRouter(prefix=API_PREFIX, responses=ERROR_RESPONSES)

    @api.get("/health", tags=["health"])
    def health() -> Health:
        return Health(status="ok")

    for router in (
        auth.auth,
        auth.users,
        lookup.router,
        homes.router,
        public.demo,
        public.public,
        public.model,
    ):
        api.include_router(router)
    app.include_router(api)
    _drop_422_from_openapi(app)
    return app


def _drop_422_from_openapi(app: FastAPI) -> None:
    """Validation errors are returned as 400 `validation` (CONTRACT §3), never 422."""
    original = app.openapi

    def openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = original()
        for ops in schema.get("paths", {}).values():
            for op in ops.values():
                op.get("responses", {}).pop("422", None)
        schemas = schema.get("components", {}).get("schemas", {})
        schemas.pop("HTTPValidationError", None)
        schemas.pop("ValidationError", None)
        return schema

    app.openapi = openapi


app = create_app()
