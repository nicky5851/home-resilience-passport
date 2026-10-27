"""Write the app's OpenAPI schema to docs/openapi.json (no server needed).

uv run python -m scripts.export_openapi           # write
uv run python -m scripts.export_openapi --check   # exit 1 if the committed file is stale
"""

import json
import sys

from app.config import REPO_ROOT
from app.main import app

OUT = REPO_ROOT / "docs" / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    text = render()
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text() != text:
            print("docs/openapi.json is out of date. Run `make openapi` and commit the result.")
            return 1
        print("docs/openapi.json is up to date.")
        return 0
    OUT.write_text(text)
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
