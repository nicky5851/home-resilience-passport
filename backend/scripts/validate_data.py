"""Check data/reference/*.csv against CONTRACT.md §5 (`make validate-data`).

uv run python -m scripts.validate_data [directory]

Prints the file, row and column of every problem. Exits 1 if any error is found;
warnings (such as placeholder source URLs) are printed but do not fail.
"""

import sys
from pathlib import Path

from app.db.reference import REFERENCE_DIR, load_reference


def main(argv: list[str]) -> int:
    directory = Path(argv[0]) if argv else REFERENCE_DIR
    ref = load_reference(directory)
    for problem in ref.problems:
        print(problem)
    counts = ", ".join(f"{name}: {len(rows)} rows" for name, rows in ref.rows.items())
    warnings = len(ref.problems) - len(ref.errors)
    if ref.errors:
        print(f"FAILED: {len(ref.errors)} error(s), {warnings} warning(s). ({counts})")
        return 1
    print(f"OK: {counts}" + (f" ({warnings} warning(s))" if warnings else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
