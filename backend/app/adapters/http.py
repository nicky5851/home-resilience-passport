"""Outbound HTTP shared by every adapter (spec §5: 10-second timeout on every call)."""

import httpx

from app.config import EXTERNAL_TIMEOUT_S

USER_AGENT = "HomeResiliencePassport/0.1"


class UpstreamUnavailable(Exception):
    """A data source timed out, could not be reached, or sent an answer we cannot use."""

    def __init__(self, source: str) -> None:
        super().__init__(f"{source} is unavailable")
        self.source = source


def new_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=EXTERNAL_TIMEOUT_S, headers={"User-Agent": USER_AGENT})
