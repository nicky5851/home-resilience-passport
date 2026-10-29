"""HM Land Registry Price Paid Data + UK House Price Index adapters (docs/studio/N_20_function.md
§S14). Both endpoints and their field shapes **verified** live 2026-10-29:

- PPD: `https://landregistry.data.gov.uk/data/ppi/transaction-record.json
  ?propertyAddress.postcode=<POSTCODE>&min-transactionDate=<ISO date>&_pageSize=<n>`. Items carry
  `pricePaid`, `transactionDate` (RFC-822-ish, e.g. "Fri, 18 Dec 1998"), `propertyAddress.paon`
  (house number - never surfaced), `propertyType._about` (ends in `detached`/`semiDetached`/
  `terraced`/`flatMaisonette`/`other`), `transactionCategory._about` (filter to
  `standardPricePaidTransaction` only).
- HPI: `https://landregistry.data.gov.uk/data/ukhpi/region/<slug>/month/<YYYY-MM>.json`, where
  `<slug>` is the local authority name lower-cased with spaces as hyphens (**verified** for
  "Crawley" -> "crawley"; an LA with a different official LR region slug, e.g. one with "City
  of" or an apostrophe, may 404 and fall back to the synthetic path - a scope call, since a full
  name->slug lookup table was not built this session). `primaryTopic` carries
  `housePriceIndex{Detached,SemiDetached,Terraced,FlatMaisonette}` and the matching
  `averagePrice*` fields.

`PropertyType` has no Land Registry equivalent for "bungalow" or "other"; bungalows are mapped
to "detached" (most English bungalows are detached or semi; flagged as an approximation) and
"other" has no PPD/HPI mapping, so homes of that type always use the HPI-average fallback."""

from pathlib import Path

PPD_BASE = "https://landregistry.data.gov.uk/data/ppi/transaction-record.json"
HPI_BASE = "https://landregistry.data.gov.uk/data/ukhpi/region"

YEARS_BACK = 5
NEAREST_POSTCODES_RADIUS_M = 1000
NEAREST_POSTCODES_LIMIT = 30
PPD_PAGE_SIZE = 200
MAX_COMPS = 60
MIN_COMPS_FOR_MEDIAN = 5
CACHE_DAYS = 30

PPD_TYPE_FOR_PROPERTY_TYPE: dict[str, str] = {
    "detached": "detached",
    "semi_detached": "semiDetached",
    "terraced": "terraced",
    "flat": "flatMaisonette",
    "bungalow": "detached",
}

HPI_FIELD_FOR_PPD_TYPE: dict[str, str] = {
    "detached": "Detached",
    "semiDetached": "SemiDetached",
    "terraced": "Terraced",
    "flatMaisonette": "FlatMaisonette",
}

EPC_BAND_ORDER = ["A", "B", "C", "D", "E", "F", "G"]

DISCLAIMER = "Not a valuation. Lenders use a professional valuation."

GREEN_PREMIUM_CSV = Path(__file__).resolve().parents[2] / "data" / "green_premium.csv"


def load_premium_sources() -> list[dict]:
    import csv

    with GREEN_PREMIUM_CSV.open(newline="") as f:
        return [
            {
                "study": row["study"],
                "url": row["url"],
                "year": int(row["year"]),
                "pct_low": float(row["pct_per_band_step_low"]),
                "pct_high": float(row["pct_per_band_step_high"]),
            }
            for row in csv.DictReader(f)
        ]
