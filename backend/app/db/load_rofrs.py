"""Load EA "Risk of Flooding from Rivers and Sea – Postcodes in Areas at Risk" (`make flood-data`).

uv run python -m app.db.load_rofrs [--download] [path/to/zip]

Open Government Licence, no sign-up. The ZIP (about 5 MB) is downloaded into data/raw/
(git-ignored) when missing, or always with --download. It holds one CSV with one row per
postcode and a property count per likelihood band (`TOT_CNT_High`, `TOT_CNT_Medium`,
`TOT_CNT_Low`, `TOT_CNT_VeryLow`). We store the highest band with at least one property
(CONTRACT §2), one row per postcode. Rows whose `PC` is not a real postcode (the dataset's
"V…" pseudo-postcodes) are skipped. The table is replaced as a whole.
"""

import asyncio
import csv
import io
import sys
import zipfile
from pathlib import Path

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import ROFRS_DOWNLOAD_TIMEOUT_S, ROFRS_ZIP
from app.db.models import FloodPostcode
from app.db.session import get_engine, make_sessionmaker
from app.schemas import normalise_postcode

ROFRS_URL = (
    "https://environment.data.gov.uk/api/file/download"
    "?fileDataSetId=97781741-2982-4802-af2e-313fe3fd8f7e"
    "&fileName=RoFRS_Postcodes_in_Areas_at_Risk.zip"
)
POSTCODE_COLUMN = "PC"
# Highest first: the first band with a property in it wins.
BAND_COLUMNS = (
    ("high", "TOT_CNT_High"),
    ("medium", "TOT_CNT_Medium"),
    ("low", "TOT_CNT_Low"),
    ("very_low", "TOT_CNT_VeryLow"),
)
INSERT_CHUNK = 5000


class RofrsError(RuntimeError):
    pass


def download(dest: Path = ROFRS_ZIP) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    with httpx.stream(
        "GET", ROFRS_URL, timeout=ROFRS_DOWNLOAD_TIMEOUT_S, follow_redirects=True
    ) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    tmp.replace(dest)


def read_bands(zip_path: Path) -> dict[str, str]:
    """{postcode: highest band} from the ZIP's CSV."""
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise RofrsError(f"Expected one CSV in {zip_path.name}, found {len(names)}")
        with z.open(names[0]) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig"))
            needed = {POSTCODE_COLUMN, *(col for _, col in BAND_COLUMNS)}
            missing = needed - set(reader.fieldnames or ())
            if missing:
                raise RofrsError(f"{names[0]} is missing columns: {', '.join(sorted(missing))}")
            bands: dict[str, str] = {}
            for row in reader:
                try:
                    postcode = normalise_postcode(row[POSTCODE_COLUMN])
                except ValueError:
                    continue  # pseudo-postcode
                band = next((b for b, col in BAND_COLUMNS if _count(row[col]) > 0), None)
                if band is not None:
                    bands[postcode] = band
    return bands


def _count(v: str | None) -> int:
    try:
        return int(v or 0)
    except ValueError:
        return 0


async def load(engine: AsyncEngine, bands: dict[str, str]) -> int:
    rows = [{"postcode": pc, "band": band} for pc, band in bands.items()]
    async with make_sessionmaker(engine)() as session, session.begin():
        await session.execute(delete(FloodPostcode))
        for i in range(0, len(rows), INSERT_CHUNK):
            await session.execute(insert(FloodPostcode), rows[i : i + INSERT_CHUNK])
    return len(rows)


async def _main(argv: list[str]) -> int:
    paths = [a for a in argv if not a.startswith("--")]
    zip_path = Path(paths[0]) if paths else ROFRS_ZIP
    if "--download" in argv or not zip_path.exists():
        print(f"Downloading RoFRS postcodes to {zip_path} ...")
        download(zip_path)
    try:
        bands = read_bands(zip_path)
    except (RofrsError, zipfile.BadZipFile) as e:
        print(f"RoFRS load refused: {e}")
        return 1
    engine = get_engine()
    try:
        n = await load(engine, bands)
    finally:
        await engine.dispose()
    print(f"Loaded {n} postcodes into flood_postcodes")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main(sys.argv[1:])))
