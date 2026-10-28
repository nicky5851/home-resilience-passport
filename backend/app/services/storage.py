"""Certificate files (CONTRACT §6, spec N14): one interface, `LocalStorage` in M1.

`R2Storage` (a private Cloudflare R2 bucket) is added in N17 behind the same three methods.
Keys are always `<uuid>.<ext>` made by `new_key`, never a user's file name, so a key can't
point outside the storage root.
"""

import re
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.config import UPLOAD_DIR

KEY = re.compile(r"^[0-9a-f]{32}\.(pdf|jpg|png)$")


def new_key(ext: str) -> str:
    key = f"{uuid.uuid4().hex}.{ext}"
    _check(key)
    return key


def _check(key: str) -> None:
    if not KEY.fullmatch(key):
        raise ValueError(f"not a storage key: {key!r}")


class Storage(Protocol):
    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes | None: ...
    def delete(self, key: str) -> None: ...


class LocalStorage:
    """Files in a local folder (`backend/uploads/`, git-ignored)."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or UPLOAD_DIR

    def put(self, key: str, data: bytes) -> None:
        _check(key)
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.root / f".{key}.part"
        tmp.write_bytes(data)
        tmp.replace(self.root / key)  # never a half-written certificate

    def get(self, key: str) -> bytes | None:
        _check(key)
        path = self.root / key
        return path.read_bytes() if path.exists() else None

    def delete(self, key: str) -> None:
        _check(key)
        (self.root / key).unlink(missing_ok=True)


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    return LocalStorage()
