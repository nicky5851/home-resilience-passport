"""Settings and constants for the API.

Every timeout, TTL and limit from docs/CODING_SPEC.md lives here as a named constant, never inline.
Environment-dependent values come from `.env` (repo root) through `Settings`.
Scoring thresholds and weights live in `app/scoring/config.py` (L), not here.
"""

from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

# --- API ---------------------------------------------------------------------------------
API_PREFIX = "/api/v1"
MAX_LIST_ITEMS = 50  # CONTRACT §3: no pagination in M1

# --- Outbound calls (spec §5) ------------------------------------------------------------
EXTERNAL_TIMEOUT_S = 10.0
LLM_TIMEOUT_S = 8.0

# --- Cache TTLs (spec §5) ----------------------------------------------------------------
POSTCODE_CACHE_TTL = timedelta(days=30)
EPC_CACHE_TTL = timedelta(days=30)
FLOOD_WARNINGS_CACHE_TTL = timedelta(minutes=15)
CLIMATE_CACHE_TTL = timedelta(days=90)
CLIMATE_CACHE_ROUND_DEGREES = 1  # lat/lon rounded to 0.1°

# --- Hazard data (CONTRACT §2) -----------------------------------------------------------
FLOOD_WARNINGS_RADIUS_KM = 5
CLIMATE_MODEL = "EC_Earth3P_HR"
CLIMATE_BASELINE_YEARS = (1991, 2020)
CLIMATE_FUTURE_YEARS = (2041, 2050)
HOT_DAY_THRESHOLD_C = 28.0  # CONTRACT §2: 30 °C gave 0.83 days/yr in London (N2 check)
HEAVY_RAIN_THRESHOLD_MM = 20.0

# --- Auth (CONTRACT §4) ------------------------------------------------------------------
AUTH_COOKIE_NAME = "hrp_auth"
AUTH_COOKIE_LIFETIME = timedelta(days=7)
PASSWORD_MIN_LENGTH = 10
PRIVACY_VERSION = "2026-10-26"

# --- Rate limits (CONTRACT §3): (requests, window) ---------------------------------------
RATE_LIMIT_LOGIN = (5, timedelta(minutes=1))  # per IP
RATE_LIMIT_REGISTER = (10, timedelta(hours=1))  # per IP
RATE_LIMIT_ASSESS = (30, timedelta(hours=1))  # per user

# --- Uploads (CONTRACT §6) ---------------------------------------------------------------
UPLOAD_MAX_BYTES = 5 * 1024 * 1024
CERTIFICATE_NAME_MAX_CHARS = 100
UPLOAD_DIR = REPO_ROOT / "backend" / "uploads"

# --- Text limits (CONTRACT §1 rule 8) ----------------------------------------------------
TEXT_MAX_CHARS = 140
EXPLANATION_MAX_CHARS = 200

# --- Sharing (spec N14) ------------------------------------------------------------------
SHARE_TOKEN_BYTES = 24


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+asyncpg://hrp:hrp@localhost:5432/hrp"
    auth_secret: str = "dev-only-secret-change-me-0123456789abcdef"
    allowed_origins: str = "http://localhost:3000"

    epc_api_token: str | None = None

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    llm_daily_call_limit: int = 300

    storage_backend: Literal["local", "r2"] = "local"

    @property
    def allowed_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
