"""The `api_cache` table: adapter answers kept for their TTL (spec §5). No personal data.

The cache is best-effort: if the database cannot be reached, reads miss and writes are dropped,
so a data source that is up still answers (spec §5: the app keeps working when a part is down).
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApiCache

log = logging.getLogger(__name__)


class Cache(Protocol):
    async def get(self, key: str) -> dict[str, Any] | None: ...

    async def put(self, key: str, source: str, value: dict[str, Any], ttl: timedelta) -> None: ...


class DbCache:
    """One request's cache. Adapters run in parallel (`asyncio.gather`) but an AsyncSession
    allows one operation at a time, so every call takes the lock first."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> dict[str, Any] | None:
        stmt = select(ApiCache.value).where(
            ApiCache.key == key, ApiCache.expires_at > datetime.now(UTC)
        )
        async with self._lock:
            try:
                return await self.session.scalar(stmt)
            except (SQLAlchemyError, OSError) as e:
                await self._failed("read", e)
                return None

    async def put(self, key: str, source: str, value: dict[str, Any], ttl: timedelta) -> None:
        now = datetime.now(UTC)
        row = {"key": key, "source": source, "value": value, "fetched_at": now}
        stmt = insert(ApiCache).values(**row, expires_at=now + ttl)
        stmt = stmt.on_conflict_do_update(
            index_elements=[ApiCache.key],
            set_={"value": stmt.excluded.value, "fetched_at": now, "expires_at": now + ttl},
        )
        async with self._lock:
            try:
                await self.session.execute(stmt)
                await self.session.commit()
            except (SQLAlchemyError, OSError) as e:
                await self._failed("write", e)

    async def _failed(self, action: str, e: Exception) -> None:
        # The key may contain a postcode, so only the error type is logged (CONTRACT §6).
        log.warning(
            "api_cache %s failed (%s); continuing without the cache", action, type(e).__name__
        )
        try:
            await self.session.rollback()
        except (SQLAlchemyError, OSError):
            pass
