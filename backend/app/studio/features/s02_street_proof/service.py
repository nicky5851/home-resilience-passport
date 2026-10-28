"""Grouping, peer matching, improver detection and upgrade inference — all pure and unit-tested
against hand-written certificates. `build_street_proof` is the only part that touches the
network (postcodes.io + the EPC register), via the shared adapters."""

import asyncio
import statistics
from collections import defaultdict

from app.adapters.cache import Cache
from app.adapters.epc import certificate_by_number as fetch_certificate
from app.adapters.epc import search_postcode_rows
from app.adapters.http import UpstreamUnavailable
from app.adapters.postcodes import nearest_postcodes
from app.schemas import PropertyFacts
from app.studio.features.s02_street_proof.cert import (
    Cert,
    address_key,
    cert_from_raw,
    lighting_percent,
)
from app.studio.features.s02_street_proof.config import (
    AGE_BAND_ORDER,
    FETCH_BUDGET_S,
    FETCH_CONCURRENCY,
    IMPROVER_SAP_GAIN,
    MAX_STORIES,
    MAX_UPGRADE_ROWS,
    MIN_PEERS_FOR_STORIES,
    UPGRADE_RULES,
    fuel_family,
)
from app.studio.features.s02_street_proof.schemas import BandCount, Story, StreetProof, UpgradeRow


def group_by_address(
    rows: list[dict], certs_by_number: dict[str, dict | None]
) -> dict[str, list[Cert]]:
    groups: dict[str, list[Cert]] = defaultdict(list)
    for row in rows:
        number = row.get("certificateNumber")
        cert = cert_from_raw(row, certs_by_number.get(number))
        if cert is not None:
            groups[cert.address_key].append(cert)
    for certs in groups.values():
        certs.sort(key=lambda c: c.registered)
    return groups


def _age_index(band: str | None) -> int | None:
    return AGE_BAND_ORDER.index(band) if band in AGE_BAND_ORDER else None


def is_peer(cert: Cert, home: PropertyFacts) -> bool:
    if cert.property_type != home.property_type:
        return False
    if (cert.built_form or "").lower() != (home.built_form or "").lower():
        return False
    if fuel_family(home.main_fuel) != "unknown" and cert.fuel_family != fuel_family(home.main_fuel):
        return False
    hi, ci = _age_index(home.construction_age_band), _age_index(cert.age_band)
    if hi is not None and ci is not None and abs(hi - ci) > 1:
        return False
    return True


def peer_definition_text(home: PropertyFacts, radius_m: int) -> str:
    kind = (home.property_type or "home").replace("_", "-")
    age = f" built {home.construction_age_band}" if home.construction_age_band else ""
    fuel = fuel_family(home.main_fuel)
    fuel_text = f", {fuel} heated" if fuel != "unknown" else ""
    km = radius_m / 1000
    return f"{kind.capitalize()} homes{age}{fuel_text}, within {km:g} km".strip()


def is_improver(certs: list[Cert]) -> bool:
    if len(certs) < 2 or certs[0].sap is None or certs[-1].sap is None:
        return False
    return certs[-1].sap - certs[0].sap >= IMPROVER_SAP_GAIN


def _newly_insulated(earliest_desc: str, latest_desc: str) -> bool:
    """`"no insulation"` itself contains the substring "insulat", so a plain `"insulat" in text`
    check can't tell "not insulated" from "insulated" — this looks for the negative wording
    going away instead."""
    was_not_insulated = "no insulation" in earliest_desc
    is_now_insulated = "insulat" in latest_desc and "no insulation" not in latest_desc
    return was_not_insulated and is_now_insulated


def detect_upgrades(earliest: Cert, latest: Cert) -> list[str]:
    detected = []
    if _newly_insulated(earliest.wall_desc, latest.wall_desc):
        detected.append("wall_insulation")
    if _newly_insulated(earliest.roof_desc, latest.roof_desc):
        detected.append("loft_insulation")
    if "single" in earliest.window_desc and (
        "double" in latest.window_desc or "triple" in latest.window_desc
    ):
        detected.append("glazing")
    if "heat pump" in latest.heating_desc and "heat pump" not in earliest.heating_desc:
        detected.append("heat_pump")
    if "photovoltaic" in latest.other_text and "photovoltaic" not in earliest.other_text:
        detected.append("solar_pv")
    before_pct, after_pct = (
        lighting_percent(earliest.lighting_desc),
        lighting_percent(latest.lighting_desc),
    )
    if before_pct is not None and after_pct is not None and after_pct - before_pct >= 50:
        detected.append("led_lighting")
    if (
        "boiler" in earliest.heating_desc
        and "condensing" not in earliest.heating_desc
        and "condensing" in latest.heating_desc
    ):
        detected.append("boiler_upgrade")
    return detected


LABELS = dict(UPGRADE_RULES)
_REVERSE = {name: label for label, name in UPGRADE_RULES}


async def _fetch_group_rows(
    outcodes: list[str], cache: Cache, budget_s: float
) -> tuple[list[dict], bool]:
    sem = asyncio.Semaphore(FETCH_CONCURRENCY)

    async def fetch_one(pc: str) -> list[dict]:
        async with sem:
            try:
                return await search_postcode_rows(pc, cache)
            except UpstreamUnavailable:
                return []

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(fetch_one(pc) for pc in outcodes)), timeout=budget_s
        )
        return [row for rows in results for row in rows], False
    except TimeoutError:
        return [], True


async def _fetch_certificates(
    numbers: set[str], cache: Cache, budget_s: float
) -> tuple[dict[str, dict | None], bool]:
    sem = asyncio.Semaphore(FETCH_CONCURRENCY)

    async def fetch_one(number: str) -> tuple[str, dict | None]:
        async with sem:
            try:
                return number, await fetch_certificate(number, cache)
            except UpstreamUnavailable:
                return number, None

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(fetch_one(n) for n in numbers)), timeout=budget_s
        )
        return dict(results), False
    except TimeoutError:
        return {}, True


async def build_street_proof(
    home_property: PropertyFacts,
    home_sap: int | None,
    lat: float,
    lon: float,
    radius_m: int,
    cache: Cache,
) -> StreetProof:
    partial = False
    try:
        outcodes = await nearest_postcodes(lat, lon, radius_m, limit=50)
    except UpstreamUnavailable:
        outcodes, partial = [], True

    rows, timed_out = await _fetch_group_rows(outcodes, cache, FETCH_BUDGET_S)
    partial = partial or timed_out

    # Only addresses with 2+ certificates need their full history fetched to find improvers;
    # single-certificate addresses still need their one certificate for SAP/peer matching.
    by_address: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_address[address_key(row)].append(row)

    numbers_needed: set[str] = set()
    for addr_rows in by_address.values():
        addr_rows.sort(key=lambda r: r.get("registrationDate") or "")
        numbers_needed.add(addr_rows[0]["certificateNumber"])
        numbers_needed.add(addr_rows[-1]["certificateNumber"])

    certs_by_number, timed_out2 = await _fetch_certificates(numbers_needed, cache, FETCH_BUDGET_S)
    partial = partial or timed_out2

    groups = group_by_address(rows, certs_by_number)
    peer_groups = {
        addr: certs for addr, certs in groups.items() if certs and is_peer(certs[-1], home_property)
    }

    peers_count = len(peer_groups)
    band_counts: dict[str, int] = defaultdict(int)
    saps: list[int] = []
    for certs in peer_groups.values():
        latest = certs[-1]
        if latest.band:
            band_counts[latest.band] += 1
        if latest.sap is not None:
            saps.append(latest.sap)

    your_percentile = None
    if home_sap is not None and saps and peers_count >= MIN_PEERS_FOR_STORIES:
        your_percentile = round(100 * sum(1 for s in saps if s <= home_sap) / len(saps))

    improver_groups = {addr: c for addr, c in peer_groups.items() if is_improver(c)}
    improvers_count = len(improver_groups)
    gains = [c[-1].sap - c[0].sap for c in improver_groups.values() if c[-1].sap and c[0].sap]
    median_gain = round(statistics.median(gains)) if gains else None

    upgrade_counts: dict[str, list[int]] = defaultdict(list)
    stories: list[Story] = []
    show_detail = peers_count >= MIN_PEERS_FOR_STORIES
    for certs in improver_groups.values():
        earliest, latest = certs[0], certs[-1]
        names = detect_upgrades(earliest, latest)
        gain = (latest.sap or 0) - (earliest.sap or 0)
        for name in names:
            upgrade_counts[name].append(gain)
        if show_detail and len(stories) < MAX_STORIES and earliest.band and latest.band:
            stories.append(
                Story(
                    distance_m=round(radius_m / 2 / 100) * 100,
                    from_band=earliest.band,
                    to_band=latest.band,
                    from_sap=earliest.sap or 0,
                    to_sap=latest.sap or 0,
                    year_from=earliest.registered.year,
                    year_to=latest.registered.year,
                    upgrades=[LABELS.get(n, n) for n in names],
                )
            )

    top_upgrades = []
    if improvers_count:
        for label, name in UPGRADE_RULES[:MAX_UPGRADE_ROWS]:
            gains_for = upgrade_counts.get(name, [])
            if not gains_for:
                continue
            top_upgrades.append(
                UpgradeRow(
                    label=label,
                    share_pct=round(100 * len(gains_for) / improvers_count),
                    median_sap_gain=round(statistics.median(gains_for)) if gains_for else None,
                )
            )
        top_upgrades.sort(key=lambda u: u.share_pct, reverse=True)

    return StreetProof(
        peer_definition=peer_definition_text(home_property, radius_m),
        peers_count=peers_count,
        band_distribution=[BandCount(band=b, count=n) for b, n in sorted(band_counts.items())],
        your_sap=home_sap,
        your_percentile=your_percentile,
        improvers_count=improvers_count,
        median_sap_gain=median_gain,
        top_upgrades=top_upgrades[:MAX_UPGRADE_ROWS],
        stories=stories if show_detail else [],
        partial=partial,
        evidence=[],
        fallback_used=False,
    )
