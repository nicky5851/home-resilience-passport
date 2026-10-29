"""Task-rule evaluation (docs/studio/N_20_function.md §S17 Algorithm 2), pure and tested."""

from datetime import date, timedelta

from app.studio.features.s17_care_calendar.climatology import REFERENCE_YEAR

LEVEL_ORDER = {"low": 0, "medium": 1, "high": 2}


class TaskContext:
    def __init__(
        self,
        *,
        main_heating: str | None,
        main_fuel: str | None,
        storm_level: str,
        river_sea_flood_level: str,
        completed_measure_ids: list[str],
    ) -> None:
        self.main_heating = (main_heating or "").lower()
        self.main_fuel = (main_fuel or "").lower()
        self.storm_level = storm_level
        self.flood_measure = any(
            m in completed_measure_ids for m in ("flood-door", "flood-plan-kit")
        )
        self.flood_risk_at_least_medium = LEVEL_ORDER.get(river_sea_flood_level, 0) >= 1
        self.measure_ids = completed_measure_ids


def resolve_month(
    schedule: dict, first_frost_avg: str | None, wettest_month: int, windiest_month: int
) -> int | None:
    kind = schedule["type"]
    if kind == "fixed_month":
        return schedule["month"]
    if kind == "before_first_frost":
        if first_frost_avg is None:
            return None
        mm, dd = (int(p) for p in first_frost_avg.split("-"))
        target = date(REFERENCE_YEAR, mm, dd) - timedelta(days=schedule["days"])
        return target.month
    if kind == "before_wettest_month":
        return 12 if wettest_month == 1 else wettest_month - 1
    if kind == "after_windiest_month":
        return 1 if windiest_month == 12 else windiest_month + 1
    return None


def resolve_day(schedule: dict, first_frost_avg: str | None) -> int:
    if schedule["type"] == "before_first_frost" and first_frost_avg is not None:
        mm, dd = (int(p) for p in first_frost_avg.split("-"))
        target = date(REFERENCE_YEAR, mm, dd) - timedelta(days=schedule["days"])
        return target.day
    return 1


def condition_met(condition: dict | None, ctx: TaskContext) -> bool:
    if condition is None:
        return True
    kind = condition["type"]
    if kind == "main_heating_contains":
        return condition["value"].lower() in ctx.main_heating
    if kind == "main_fuel_is":
        return ctx.main_fuel == condition["value"].lower()
    if kind == "flood_measure_or_risk":
        return ctx.flood_measure or ctx.flood_risk_at_least_medium
    if kind == "storm_risk_at_least":
        return LEVEL_ORDER.get(ctx.storm_level, 0) >= LEVEL_ORDER[condition["value"]]
    if kind == "measure_present":
        return any(condition["value"] in m for m in ctx.measure_ids)
    return True


def months_starting_next(today: date) -> list[int]:
    return [((today.month - 1 + i) % 12) + 1 for i in range(1, 13)]


def tasks_by_month(
    all_tasks: list[dict],
    ctx: TaskContext,
    first_frost_avg: str | None,
    wettest_month: int,
    windiest_month: int,
    today: date,
) -> list[dict]:
    resolved: dict[int, list[dict]] = {m: [] for m in range(1, 13)}
    for task in all_tasks:
        if not condition_met(task.get("condition"), ctx):
            continue
        month = resolve_month(task["schedule"], first_frost_avg, wettest_month, windiest_month)
        if month is None:
            continue
        resolved[month].append(
            {
                "id": task["id"],
                "title": task["title"],
                "why": task["why"],
                "effort_minutes": task["effort_minutes"],
                "hazard": task["hazard"],
                "guidance_url": task["guidance_url"],
            }
        )
    return [{"month": m, "tasks": resolved[m]} for m in months_starting_next(today)]
