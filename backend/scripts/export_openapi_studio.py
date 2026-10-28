"""Write Studio's own OpenAPI schema to docs/openapi-studio.json (no server needed).

Studio is mounted on the real app with `include_in_schema=False` so the shared
`docs/openapi.json` never changes (docs/studio/N_20_function.md §1.4). This script builds a
throwaway app with only the Studio routers, included normally, and snapshots that instead.

uv run python -m scripts.export_openapi_studio           # write
uv run python -m scripts.export_openapi_studio --check   # exit 1 if the committed file is stale
"""

import json
import sys

from fastapi import FastAPI

from app.config import API_PREFIX, REPO_ROOT
from app.studio.router import router as studio_router

OUT = REPO_ROOT / "docs" / "openapi-studio.json"


def build_app() -> FastAPI:
    app = FastAPI(title="Resilience Studio API", version="0.1.0")
    app.include_router(studio_router, prefix=API_PREFIX)
    return app


def render() -> str:
    return json.dumps(build_app().openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    text = render()
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text() != text:
            print(f"{OUT} is out of date. Run `make studio-openapi` and commit the result.")
            return 1
        print(f"{OUT} is up to date.")
        return 0
    OUT.write_text(text)
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
