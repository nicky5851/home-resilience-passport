"""Call each Studio feature's live API once per demo home and save the response as its
fallback (docs/studio/N_20_function.md §1.7). Run with the real network available:

uv run python -m scripts.record_studio_fallbacks           # every feature that has a recorder
uv run python -m scripts.record_studio_fallbacks s06        # just one feature
"""

import asyncio
import importlib
import pkgutil
import sys

from app.studio import features as features_pkg


async def main() -> int:
    only = set(sys.argv[1:])
    for modinfo in sorted(pkgutil.iter_modules(features_pkg.__path__), key=lambda m: m.name):
        pkg_name = f"{features_pkg.__name__}.{modinfo.name}"
        meta = importlib.import_module(f"{pkg_name}.meta").META
        if only and meta.id not in only:
            continue
        try:
            record_mod = importlib.import_module(f"{pkg_name}.record")
        except ModuleNotFoundError:
            continue  # this feature calls no external API
        print(f"Recording fallbacks for {meta.id} ({meta.title})...")
        await record_mod.record_all()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
