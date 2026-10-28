"""Hotspot keyword rules (docs/studio/N_20_function.md §S01 step 1): ordered, first match wins,
checked on `f"{measure.id} {measure.name}".lower()`. Keep `services` last — it is the catch-all."""

from app.studio.features.s01_retrofit_sandbox.schemas import HotspotId

HOTSPOT_LABELS: dict[HotspotId, str] = {
    "roof": "Roof",
    "walls": "Walls",
    "windows": "Windows",
    "door": "Door",
    "ground": "Garden & drainage",
    "services": "Services",
}

HOTSPOT_RULES: list[tuple[HotspotId, tuple[str, ...]]] = [
    ("roof", ("loft", "roof", "solar", "pv")),
    ("walls", ("wall", "cladding", "render")),
    ("windows", ("glaz", "window", "shading", "shutter", "blind", "awning")),
    ("door", ("flood-door", "barrier", "air-brick", "door")),
    ("ground", ("paving", "garden", "drain", "butt", "soakaway", "tree")),
]


def hotspot_for(measure_id: str, measure_name: str) -> HotspotId:
    text = f"{measure_id} {measure_name}".lower()
    for hotspot_id, keywords in HOTSPOT_RULES:
        if any(k in text for k in keywords):
            return hotspot_id
    return "services"
