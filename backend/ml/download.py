"""Training data: a few regions of the EPC bulk download (spec §5, step N12).

uv run python -m ml.download            # `make epc-data`

The register's domestic bulk file is one 8 GB zip with a CSV per year. Instead of downloading
it, this reads the zip in place with HTTP range requests (the API redirects to a signed S3 link),
streams only the chosen years, keeps rows in the chosen regions and only the columns the model
needs, and writes `data/raw/epc_bulk.csv` (git-ignored). Needs `EPC_API_TOKEN` in `.env`.
"""

import csv
import io
import sys
import zipfile
from collections.abc import Callable

import httpx

from app.config import REPO_ROOT, get_settings

OUT = REPO_ROOT / "data" / "raw" / "epc_bulk.csv"
YEARS = (2024,)  # one recent year of certificates: about 500k homes in the three regions
REGIONS = ("E12000003", "E12000007", "E12000009")  # Yorkshire, London, South West: the demos
COLUMNS = (
    "certificate_number", "uprn", "postcode", "region", "lodgement_date", "property_type",
    "built_form", "construction_age_band", "total_floor_area", "mainheat_description",
    "main_fuel", "current_energy_rating", "co2_emissions_current",
)  # fmt: skip
CHUNK = 8 << 20
TIMEOUT_S = 120.0  # bulk transfer, not a request path
RETRIES = 3


class RangeFile(io.RawIOBase):
    """A read-only, seekable view of a remote file, fetched with HTTP Range requests.

    The register's signed S3 links expire after 30 s, so a 403 fetches a new link and retries.
    """

    def __init__(self, new_url: Callable[[], str], client: httpx.Client) -> None:
        self.new_url, self.client, self.pos = new_url, client, 0
        self.url = new_url()
        probe = self._get(0, 0)
        self.size = int(probe.headers["content-range"].split("/")[1])

    def _get(self, start: int, end: int) -> httpx.Response:
        for _ in range(RETRIES):
            res = self.client.get(self.url, headers={"Range": f"bytes={start}-{end}"})
            if res.status_code == 403:  # link expired
                self.url = self.new_url()
                continue
            if res.status_code not in (200, 206):
                break
            return res
        # Never print the signed link: it carries temporary credentials.
        raise SystemExit(f"EPC bulk file read failed (HTTP {res.status_code}).")

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.pos, io.SEEK_END: self.size}[whence]
        self.pos = base + offset
        return self.pos

    def readinto(self, buffer) -> int:  # type: ignore[no-untyped-def]
        if self.pos >= self.size or len(buffer) == 0:
            return 0
        end = min(self.pos + len(buffer), self.size) - 1
        data = self._get(self.pos, end).content
        buffer[: len(data)] = data
        self.pos += len(data)
        return len(data)


def bulk_url(client: httpx.Client) -> str:
    settings = get_settings()
    if not settings.epc_api_token:
        raise SystemExit("EPC_API_TOKEN is not set in .env (see README, 'EPC API token').")
    res = client.get(
        settings.epc_api_base_url.rstrip("/") + "/api/files/domestic/csv",
        headers={"Authorization": f"Bearer {settings.epc_api_token}"},
    )
    if res.status_code != 302 or "location" not in res.headers:
        raise SystemExit(f"EPC bulk download refused (HTTP {res.status_code}).")
    return res.headers["location"]


def keep(rows, regions: tuple[str, ...] = REGIONS):  # type: ignore[no-untyped-def]
    """Rows in the chosen regions, with only `COLUMNS`."""
    for row in rows:
        if row.get("region") in regions:
            yield [row.get(c, "") for c in COLUMNS]


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".part")
    kept = 0
    with httpx.Client(timeout=TIMEOUT_S, follow_redirects=False) as client:
        remote = RangeFile(lambda: bulk_url(client), client)
        archive = zipfile.ZipFile(io.BufferedReader(remote, CHUNK))
        with tmp.open("w", newline="") as out:
            writer = csv.writer(out)
            writer.writerow(COLUMNS)
            for year in YEARS:
                with archive.open(f"certificates-{year}.csv") as member:
                    reader = csv.DictReader(io.TextIOWrapper(member, "utf-8-sig", newline=""))
                    for i, values in enumerate(keep(reader), start=1):
                        writer.writerow(values)
                        if i % 100_000 == 0:
                            print(f"  {year}: {i:,} rows kept", flush=True)
                        kept += 1
    tmp.replace(OUT)
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}: {kept:,} certificates, years {YEARS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
