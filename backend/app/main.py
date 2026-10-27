from fastapi import APIRouter, FastAPI

from app.config import API_PREFIX, get_settings


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

    api = APIRouter(prefix=API_PREFIX)

    @api.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api)
    return app


app = create_app()
