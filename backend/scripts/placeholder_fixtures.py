"""Write placeholder demo-home fixtures (spec N2).

Inputs (address, household, property, inputs) are contract. Outputs (risk, score, plan, funding,
passport) are worked out here with a simple copy of spec §6/§7 so the examples look sensible; they
are NOT L's scoring and are replaced by `make fixtures` after N8.

    uv run python scripts/placeholder_fixtures.py
"""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.schemas import (
    DemoHome,
    FundingBundle,
    FundingOption,
    HazardInputs,
    Measure,
    Passport,
    Plan,
    RiskProfile,
)

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "demo_homes"
GENERATED_AT = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
NS = uuid.UUID("6f1c2a9e-1d6b-4a8e-9a43-0c4f6f0b8b11")  # stable ids across runs
PLACEHOLDER_URL = "https://example.com/placeholder-source"

# Placeholder reference rows; A's measures.csv / funding.csv replace them.
MEASURES = [
    dict(
        id="flood-door",
        name="Flood door",
        category="flood",
        hazards_reduced=["river_sea_flood", "surface_water"],
        cost_low_gbp=1500,
        cost_high_gbp=3500,
        annual_bill_saving_gbp=0,
        co2_saved_kg_per_year=0,
        resilience_points=8,
        property_types=[],
        renter_ok=False,
        needs_landlord=True,
    ),
    dict(
        id="flood-plan-kit",
        name="Flood plan and grab bag",
        category="flood",
        hazards_reduced=["river_sea_flood", "surface_water"],
        cost_low_gbp=50,
        cost_high_gbp=150,
        annual_bill_saving_gbp=0,
        co2_saved_kg_per_year=0,
        resilience_points=2,
        property_types=[],
        renter_ok=True,
        needs_landlord=False,
    ),
    dict(
        id="reflective-blinds",
        name="Thermal reflective blinds",
        category="heat",
        hazards_reduced=["overheating"],
        cost_low_gbp=100,
        cost_high_gbp=400,
        annual_bill_saving_gbp=20,
        co2_saved_kg_per_year=30,
        resilience_points=3,
        property_types=[],
        renter_ok=True,
        needs_landlord=False,
    ),
    dict(
        id="external-shutters",
        name="External window shutters",
        category="heat",
        hazards_reduced=["overheating"],
        cost_low_gbp=800,
        cost_high_gbp=2500,
        annual_bill_saving_gbp=0,
        co2_saved_kg_per_year=0,
        resilience_points=6,
        property_types=[],
        renter_ok=False,
        needs_landlord=True,
    ),
    dict(
        id="roof-fixings",
        name="Roof and ridge tile fixings",
        category="storm",
        hazards_reduced=["storm"],
        cost_low_gbp=400,
        cost_high_gbp=1500,
        annual_bill_saving_gbp=0,
        co2_saved_kg_per_year=0,
        resilience_points=5,
        property_types=["detached", "semi_detached", "terraced", "bungalow"],
        renter_ok=False,
        needs_landlord=True,
    ),
    dict(
        id="drain-survey",
        name="Drain survey and repair",
        category="subsidence",
        hazards_reduced=["subsidence"],
        cost_low_gbp=200,
        cost_high_gbp=1200,
        annual_bill_saving_gbp=0,
        co2_saved_kg_per_year=0,
        resilience_points=4,
        property_types=["detached", "semi_detached", "terraced", "bungalow"],
        renter_ok=False,
        needs_landlord=True,
    ),
    dict(
        id="loft-insulation",
        name="Loft insulation top-up",
        category="carbon",
        hazards_reduced=[],
        cost_low_gbp=400,
        cost_high_gbp=900,
        annual_bill_saving_gbp=250,
        co2_saved_kg_per_year=600,
        resilience_points=6,
        property_types=["detached", "semi_detached", "terraced", "bungalow"],
        renter_ok=False,
        needs_landlord=True,
    ),
    dict(
        id="led-lighting",
        name="LED lighting throughout",
        category="carbon",
        hazards_reduced=[],
        cost_low_gbp=50,
        cost_high_gbp=200,
        annual_bill_saving_gbp=60,
        co2_saved_kg_per_year=80,
        resilience_points=2,
        property_types=[],
        renter_ok=True,
        needs_landlord=False,
    ),
]
for m in MEASURES:
    m["source_url"] = PLACEHOLDER_URL

FUNDING = [
    dict(
        id="boiler-upgrade-scheme",
        name="Boiler Upgrade Scheme",
        provider="UK Government",
        kind="grant",
        max_amount_gbp=7500,
        apr_percent=None,
        income_bands=[],
        tenures=["owner_occupier", "landlord"],
        categories=["carbon"],
        is_mock=False,
        source_url="https://www.gov.uk/apply-boiler-upgrade-scheme",
    ),
    dict(
        id="eco4",
        name="Energy Company Obligation (ECO4)",
        provider="Energy suppliers",
        kind="grant",
        max_amount_gbp=None,
        apr_percent=None,
        income_bands=["under_20k"],
        tenures=[],
        categories=["carbon"],
        is_mock=False,
        source_url="https://www.gov.uk/energy-company-obligation",
    ),
    dict(
        id="lloyds-green-cashback",
        name="Green home cashback",
        provider="Lloyds (illustrative)",
        kind="cashback",
        max_amount_gbp=500,
        apr_percent=None,
        income_bands=[],
        tenures=["owner_occupier"],
        categories=[],
        is_mock=True,
        source_url="",
    ),
    dict(
        id="lloyds-insurance-discount",
        name="Flood resilience insurance discount",
        provider="Lloyds (illustrative)",
        kind="insurance_discount",
        max_amount_gbp=100,
        apr_percent=None,
        income_bands=[],
        tenures=[],
        categories=["flood"],
        is_mock=True,
        source_url="",
    ),
    dict(
        id="lloyds-home-improvement-loan",
        name="Home improvement loan",
        provider="Lloyds (illustrative)",
        kind="loan",
        max_amount_gbp=25000,
        apr_percent=6.9,
        income_bands=[],
        tenures=[],
        categories=[],
        is_mock=True,
        source_url="",
    ),
]

# address, household, property, inputs, hazard_shown per demo home.
HOMES = {
    "flood-terrace": dict(
        hazard_shown="river_sea_flood",
        address=dict(
            line1="12 Fishergate Row",
            postcode="YO1 9TJ",
            lat=53.957263,
            lon=-1.076686,
            local_authority="York",
            country="england",
        ),
        household=dict(
            tenure="owner_occupier",
            income_band="20k_40k",
            budget_gbp=5000,
            priorities=["flood_safety", "lower_bills"],
            vulnerable=True,
        ),
        property=dict(
            property_type="terraced",
            built_form="Mid-Terrace",
            construction_age_band="1900-1929",
            floor_area_m2=82.0,
            floor_level=0,
            main_heating="Boiler and radiators, mains gas",
            main_fuel="mains gas",
            epc_rating="D",
            epc_score=58,
            co2_tonnes_per_year=3.4,
        ),
        inputs=dict(
            rofrs_band="high",
            active_flood_warnings=1,
            hot_days_baseline=1.5,
            hot_days_2050=4.0,
            heavy_rain_days_baseline=4.0,
            heavy_rain_days_2050=5.5,
            max_wind_baseline_kmh=44.0,
            max_wind_2050_kmh=46.0,
            subsidence_signal="none_reported",
        ),
    ),
    "coastal-bungalow": dict(
        hazard_shown="storm",
        address=dict(
            line1="3 Harbour View",
            postcode="TR18 3JA",
            lat=50.128457,
            lon=-5.546696,
            local_authority="Cornwall",
            country="england",
        ),
        household=dict(
            tenure="owner_occupier",
            income_band="under_20k",
            budget_gbp=2000,
            priorities=["lower_bills", "comfort"],
            vulnerable=None,
        ),
        property=dict(
            property_type="bungalow",
            built_form="Detached",
            construction_age_band="1950-1966",
            floor_area_m2=68.0,
            floor_level=0,
            main_heating="Electric storage heaters",
            main_fuel="electricity",
            epc_rating="E",
            epc_score=45,
            co2_tonnes_per_year=4.1,
        ),
        inputs=dict(
            rofrs_band="very_low",
            active_flood_warnings=0,
            hot_days_baseline=0.2,
            hot_days_2050=1.0,
            heavy_rain_days_baseline=9.0,
            heavy_rain_days_2050=11.0,
            max_wind_baseline_kmh=66.0,
            max_wind_2050_kmh=70.0,
            subsidence_signal="unknown",
        ),
    ),
    "city-top-flat": dict(
        hazard_shown="overheating",
        address=dict(
            line1="Flat 51, 8 Commercial Street",
            postcode="E1 8NG",
            lat=51.514481,
            lon=-0.069743,
            local_authority="Tower Hamlets",
            country="england",
        ),
        household=dict(
            tenure="private_renter",
            income_band="40k_60k",
            budget_gbp=500,
            priorities=["comfort", "lower_bills"],
            vulnerable=False,
        ),
        property=dict(
            property_type="flat",
            built_form="Mid-Terrace",
            construction_age_band="2007 onwards",
            floor_area_m2=54.0,
            floor_level=5,
            top_floor=True,
            main_heating="Community heating",
            main_fuel="mains gas",
            epc_rating="B",
            epc_score=82,
            co2_tonnes_per_year=1.2,
        ),
        inputs=dict(
            rofrs_band="very_low",
            active_flood_warnings=0,
            hot_days_baseline=6.0,
            hot_days_2050=16.0,
            heavy_rain_days_baseline=3.5,
            heavy_rain_days_2050=4.5,
            max_wind_baseline_kmh=38.0,
            max_wind_2050_kmh=40.0,
            subsidence_signal="unknown",
        ),
    ),
    "clay-semi": dict(
        hazard_shown="subsidence",
        address=dict(
            line1="27 Court Road",
            postcode="SE9 3AB",
            lat=51.439138,
            lon=0.053111,
            local_authority="Greenwich",
            country="england",
        ),
        household=dict(
            tenure="owner_occupier",
            income_band="60k_100k",
            budget_gbp=15000,
            priorities=["home_value", "lower_carbon"],
            vulnerable=False,
        ),
        property=dict(
            property_type="semi_detached",
            built_form="Semi-Detached",
            construction_age_band="1930-1949",
            floor_area_m2=96.0,
            floor_level=0,
            main_heating="Boiler and radiators, mains gas",
            main_fuel="mains gas",
            epc_rating="D",
            epc_score=63,
            co2_tonnes_per_year=3.9,
        ),
        inputs=dict(
            rofrs_band="none",
            active_flood_warnings=0,
            hot_days_baseline=5.0,
            hot_days_2050=12.0,
            heavy_rain_days_baseline=3.5,
            heavy_rain_days_2050=4.5,
            max_wind_baseline_kmh=40.0,
            max_wind_2050_kmh=41.0,
            subsidence_signal="clay_reported",
        ),
    ),
    "rural-cottage": dict(
        hazard_shown="low_risk",
        address=dict(
            line1="Rose Cottage, 4 Hill Lane",
            postcode="GL54 1HP",
            lat=51.923735,
            lon=-1.715425,
            local_authority="Cotswold",
            country="england",
        ),
        household=dict(
            tenure="owner_occupier",
            income_band="over_100k",
            budget_gbp=25000,
            priorities=["lower_carbon", "home_value"],
            vulnerable=False,
        ),
        property=dict(
            property_type="detached",
            built_form="Detached",
            construction_age_band="before 1900",
            floor_area_m2=140.0,
            floor_level=0,
            main_heating="Boiler and radiators, oil",
            main_fuel="oil",
            epc_rating="E",
            epc_score=41,
            co2_tonnes_per_year=7.8,
        ),
        inputs=dict(
            rofrs_band="none",
            active_flood_warnings=0,
            hot_days_baseline=2.0,
            hot_days_2050=4.5,
            heavy_rain_days_baseline=5.0,
            heavy_rain_days_2050=6.0,
            max_wind_baseline_kmh=46.0,
            max_wind_2050_kmh=48.0,
            subsidence_signal="none_reported",
        ),
    ),
}

STEP = {"low": 0, "medium": 1, "high": 2}
NAMES = ["low", "medium", "high"]
MAX_POINTS = {"flood": 30, "heat": 20, "storm": 10, "subsidence": 10, "carbon": 30}
HAZARD_COMPONENT = {
    "river_sea_flood": "flood",
    "overheating": "heat",
    "storm": "storm",
    "subsidence": "subsidence",
}
BAND_MID = {"A": 96, "B": 86, "C": 75, "D": 61, "E": 47, "F": 30, "G": 10}


def _bump(level: str, up: bool) -> str:
    return NAMES[min(2, STEP[level] + (1 if up else 0))]


def _by_threshold(v: float | None, lo: float, hi: float) -> str:
    if v is None:
        return "medium"
    return "low" if v < lo else ("medium" if v <= hi else "high")


def risk_for(inp: dict, prop: dict) -> dict:
    flood = {
        "none": "low",
        "very_low": "low",
        "low": "medium",
        "medium": "high",
        "high": "high",
        None: "medium",
    }[inp["rofrs_band"]]
    flood = _bump(flood, inp["active_flood_warnings"] > 0)
    heat_up = bool(prop.get("top_floor")) or prop.get("epc_rating") in ("A", "B")
    heat_t = _bump(_by_threshold(inp["hot_days_baseline"], 5, 15), heat_up)
    heat_f = _bump(_by_threshold(inp["hot_days_2050"], 5, 15), heat_up)
    storm_t = _by_threshold(inp["max_wind_baseline_kmh"], 50, 65)
    storm_f = _by_threshold(inp["max_wind_2050_kmh"], 50, 65)
    subs = {
        "none_reported": "low",
        "unknown": "medium",
        "clay_reported": "high",
        "cracks_reported": "high",
    }[inp["subsidence_signal"]]
    band = (inp["rofrs_band"] or "unknown").replace("_", " ")
    hot_b, hot_f = inp["hot_days_baseline"], inp["hot_days_2050"]
    w_b, w_f = inp["max_wind_baseline_kmh"], inp["max_wind_2050_kmh"]
    return {
        "levels": [
            dict(
                hazard="river_sea_flood",
                today=flood,
                y2050=flood,
                why=f"The Environment Agency rates flood risk here as {band}.",
                data_source="Environment Agency",
            ),
            dict(
                hazard="overheating",
                today=heat_t,
                y2050=heat_f,
                why=f"About {hot_f:.0f} hot days a year by 2050, up from {hot_b:.0f} today.",
                data_source="Open-Meteo (CMIP6)",
            ),
            dict(
                hazard="storm",
                today=storm_t,
                y2050=storm_f,
                why=f"Strongest winds around {w_f:.0f} km/h by 2050, from {w_b:.0f} km/h today.",
                data_source="Open-Meteo (CMIP6)",
            ),
            dict(
                hazard="subsidence",
                today=subs,
                y2050=subs,
                why="Based on what you told us about your soil and walls.",
                data_source="Your answer",
            ),
            dict(
                hazard="surface_water",
                today="medium",
                y2050="medium",
                why="Surface-water data is coming in a later version",
                data_source="Environment Agency",
            ),
        ],
        "generated_at": GENERATED_AT.isoformat().replace("+00:00", "Z"),
    }


def _band(v: int) -> str:
    for band, floor in (("A", 85), ("B", 70), ("C", 55), ("D", 40), ("E", 25), ("F", 10)):
        if v >= floor:
            return band
    return "G"


def score_for(risk: dict, prop: dict, measures: list[dict]) -> dict:
    by_hazard = {lv["hazard"]: lv["y2050"] for lv in risk["levels"]}
    frac = {"low": 1.0, "medium": 0.5, "high": 0.1}
    pts = {comp: MAX_POINTS[comp] * frac[by_hazard[h]] for h, comp in HAZARD_COMPONENT.items()}
    if prop.get("epc_score") is not None:
        pts["carbon"] = prop["epc_score"] * 0.3
    elif prop.get("epc_rating"):
        pts["carbon"] = BAND_MID[prop["epc_rating"]] * 0.3
    else:
        pts["carbon"] = 15.0
    for m in measures:
        pts[m["category"]] += m["resilience_points"]
    comps = []
    for name in ("flood", "heat", "storm", "subsidence", "carbon"):
        p = round(min(pts[name], MAX_POINTS[name]), 1)
        reason = (
            f"Based on your EPC score of {prop.get('epc_score')}."
            if name == "carbon"
            else f"Your {name} risk by 2050 sets these points."
        )
        comps.append(dict(name=name, points=p, max_points=float(MAX_POINTS[name]), reason=reason))
    value = max(0, min(100, round(sum(c["points"] for c in comps))))
    return dict(value=value, band=_band(value), components=comps, version="v1")


def plan_for(risk: dict, prop: dict, household: dict) -> dict:
    renter = household["tenure"] in ("private_renter", "social_renter")
    base = score_for(risk, prop, [])["value"]
    cands = [
        m
        for m in MEASURES
        if (not m["property_types"] or prop["property_type"] in m["property_types"])
        and not (renter and m["needs_landlord"])
    ]
    scored = []
    for m in cands:
        uplift = score_for(risk, prop, [m])["value"] - base
        mid = max(50, (m["cost_low_gbp"] + m["cost_high_gbp"]) / 2)
        scored.append((-(uplift / mid), m["cost_low_gbp"], m["id"], m, uplift))
    scored.sort(key=lambda t: t[:3])
    items, spent, chosen = [], 0, []
    for rank, (_, _, _, m, uplift) in enumerate(scored, start=1):
        selected = uplift > 0 and spent + m["cost_low_gbp"] <= household["budget_gbp"]
        if selected:
            spent += m["cost_low_gbp"]
            chosen.append(m)
        saving = m["annual_bill_saving_gbp"]
        mid = (m["cost_low_gbp"] + m["cost_high_gbp"]) / 2
        hazard = m["hazards_reduced"][0].replace("_", " ") if m["hazards_reduced"] else "carbon"
        items.append(
            dict(
                measure=m,
                rank=rank,
                score_uplift=uplift,
                payback_years=round(mid / saving, 1) if saving else None,
                explanation=(
                    f"{m['name']} reduces your {hazard} risk and adds about {uplift} points "
                    f"for £{m['cost_low_gbp']}–£{m['cost_high_gbp']}."
                ),
                selected=selected,
            )
        )
    return dict(
        items=items,
        total_cost_low_gbp=sum(m["cost_low_gbp"] for m in chosen),
        total_cost_high_gbp=sum(m["cost_high_gbp"] for m in chosen),
        projected_score=score_for(risk, prop, chosen),
        explanation_source="template",
    )


def funding_for(plan: dict, household: dict) -> dict:
    chosen = [i["measure"] for i in plan["items"] if i["selected"]]
    cats = {m["category"] for m in chosen}
    cost = plan["total_cost_low_gbp"]
    order = {
        "grant": 0,
        "cashback": 1,
        "insurance_discount": 2,
        "loan": 3,
        "mortgage_further_advance": 3,
    }
    ok = [
        f
        for f in FUNDING
        if (not f["income_bands"] or household["income_band"] in f["income_bands"])
        and (not f["tenures"] or household["tenure"] in f["tenures"])
        and (not f["categories"] or cats & set(f["categories"]))
    ]
    ok.sort(key=lambda f: (order[f["kind"]], f["apr_percent"] or 0, f["id"]))
    lines, remaining = [], cost
    for f in ok:
        if f["kind"] in ("loan", "mortgage_further_advance") or remaining <= 0:
            continue
        eligible = sum(
            m["cost_low_gbp"]
            for m in chosen
            if not f["categories"] or m["category"] in f["categories"]
        )
        amount = min(remaining, eligible, f["max_amount_gbp"] or eligible)
        if amount > 0:
            remaining -= amount
            note = "Illustrative product." if f["is_mock"] else "You appear to qualify."
            lines.append(dict(option=f, amount_gbp=amount, note=note))
    monthly = None
    loans = [f for f in ok if f["kind"] in ("loan", "mortgage_further_advance")]
    if remaining > 0 and loans:
        loan = min(loans, key=lambda f: f["apr_percent"] or 0)
        r, n = (loan["apr_percent"] or 0) / 100 / 12, 60
        monthly = round(remaining * r / (1 - (1 + r) ** -n)) if r else round(remaining / n)
        lines.append(
            dict(
                option=loan,
                amount_gbp=remaining,
                note="Illustrative loan over 5 years for the remaining cost.",
            )
        )
    covered = sum(
        ln["amount_gbp"]
        for ln in lines
        if ln["option"]["kind"] not in ("loan", "mortgage_further_advance")
    )
    return dict(lines=lines, covered_gbp=covered, gap_gbp=cost - covered, monthly_cost_gbp=monthly)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, h in HOMES.items():
        prop = {**h["property"], "source": "demo"}
        if prop["property_type"] != "flat":
            prop.setdefault("top_floor", None)
        inputs = {**h["inputs"], "property": prop}
        risk = risk_for(h["inputs"], prop)
        score = score_for(risk, prop, [])
        plan = plan_for(risk, prop, h["household"])
        funding = funding_for(plan, h["household"])
        home_id = uuid.uuid5(NS, slug)
        passport = dict(
            home_id=str(home_id),
            address=h["address"],
            property=prop,
            household=h["household"],
            latest_risk=risk,
            latest_score=score,
            plan=plan,
            events=[
                dict(
                    id=str(uuid.uuid5(NS, f"{slug}/assessed")),
                    kind="assessed",
                    at=risk["generated_at"],
                    score_after=score["value"],
                    detail={},
                )
            ],
            share_token=None,
        )
        fixture = dict(
            slug=slug,
            hazard_shown=h["hazard_shown"],
            address=h["address"],
            household=h["household"],
            property=prop,
            inputs=inputs,
            risk=risk,
            score=score,
            plan=plan,
            funding=funding,
            passport=passport,
        )

        # Validate every part, then write the normalised (every-field-present) form.
        demo = DemoHome.model_validate({k: fixture[k] for k in DemoHome.model_fields})
        out = demo.model_dump(mode="json")
        out["inputs"] = HazardInputs.model_validate(inputs).model_dump(mode="json")
        out["passport"] = Passport.model_validate(passport).model_dump(mode="json")
        RiskProfile.model_validate(risk), Plan.model_validate(plan)
        FundingBundle.model_validate(funding)
        for m in MEASURES:
            Measure.model_validate(m)
        for f in FUNDING:
            FundingOption.model_validate(f)
        ordered = {
            k: out[k]
            for k in (
                "slug",
                "hazard_shown",
                "address",
                "household",
                "property",
                "inputs",
                "risk",
                "score",
                "plan",
                "funding",
                "passport",
            )
        }
        path = OUT / f"{slug}.json"
        path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n")
        print(
            f"{slug}: score {score['value']} ({score['band']}), "
            f"{sum(i['selected'] for i in plan['items'])} selected, gap £{funding['gap_gbp']}"
        )


if __name__ == "__main__":
    main()
