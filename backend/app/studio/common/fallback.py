"""Recorded responses for the 5 demo homes, so every feature works with the network off
(docs/studio/N_20_function.md §1.7)."""

import json
from pathlib import Path

STUDIO_DIR = Path(__file__).resolve().parents[1]
FALLBACKS_DIR = STUDIO_DIR / "fallbacks"


def load_fallback(feature: str, slug: str) -> dict | None:
    path = FALLBACKS_DIR / feature / f"{slug}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_fallback(feature: str, slug: str, data: dict) -> None:
    path = FALLBACKS_DIR / feature / f"{slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n")
