"""Studio reuses the existing `api_cache` table (spec §5) — no new cache table.

Every feature's cache keys are namespaced by feature id (e.g. `studio:s06:<outcode>`) so they
never collide with N's own adapters.
"""

from app.adapters.cache import Cache, DbCache

__all__ = ["Cache", "DbCache"]


def studio_key(feature_id: str, *parts: str) -> str:
    return f"studio:{feature_id}:" + ":".join(parts)
