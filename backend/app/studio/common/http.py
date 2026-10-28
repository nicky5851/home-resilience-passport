"""Shared outbound HTTP for Studio features: N's existing 10 s timeout, plus one retry on a
connect error (docs/studio/N_20_function.md §1.7)."""

import httpx

from app.adapters.http import UpstreamUnavailable, new_client

__all__ = ["UpstreamUnavailable", "new_client", "get_json"]


async def get_json(url: str, *, params: dict | None = None, source: str) -> dict:
    """GET `url`, retrying once on a connect error; any other failure means `source` is down."""
    async with new_client() as client:
        for attempt in range(2):
            try:
                res = await client.get(url, params=params)
            except httpx.ConnectError:
                if attempt == 0:
                    continue
                raise UpstreamUnavailable(source) from None
            except httpx.HTTPError as exc:
                raise UpstreamUnavailable(source) from exc
            if res.status_code >= 500:
                if attempt == 0:
                    continue
                raise UpstreamUnavailable(source)
            if res.status_code >= 400:
                raise UpstreamUnavailable(source)
            return res.json()
    raise UpstreamUnavailable(source)
