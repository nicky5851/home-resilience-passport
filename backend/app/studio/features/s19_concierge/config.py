"""Concierge limits, system prompt and glossary (docs/studio/N_20_function.md §S19)."""

import re
from datetime import timedelta

MAX_MESSAGES = 12
MAX_MESSAGE_CHARS = 1000
MAX_ANSWER_CHARS = 1200
MAX_SUGGESTED = 3
MAX_TOOL_ROUNDS = 4

RATE_LIMIT_CONCIERGE_USER = (20, timedelta(hours=1))  # per user
RATE_LIMIT_CONCIERGE_DEMO_IP = (10, timedelta(hours=1))  # per IP, demo refs only

SYSTEM_PROMPT = (
    "You are the Home Resilience Passport Concierge. Answer in plain English, at most 120 "
    "words. Use only the tools given to look up this home's facts; never invent a number, "
    "price, grant or saving, and only state a figure that appears in a tool result. Say a "
    "bank product or rate is 'illustrative'. For financial or structural decisions, suggest "
    "talking to a qualified adviser. If the question is off-topic, politely decline and offer "
    "to help with the home instead. You have at most 4 rounds of tool calls."
)

# Spec rule 3 (number guard): numbers with these units must come from a tool result this turn.
NUMBER_PATTERN = re.compile(
    r"£\s?[\d,]+(?:\.\d+)?|[\d,]+(?:\.\d+)?\s?%|[\d,]+(?:\.\d+)?\s?kWh|[\d,]+(?:\.\d+)?\s?kg|"
    r"[\d,]+(?:\.\d+)?\s?points",
    re.IGNORECASE,
)

# Scrubbed from user messages before anything is sent to the model (CONTRACT.md §6 rule 2).
UK_POSTCODE_PATTERN = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

GLOSSARY: dict[str, str] = {
    "epc": "The Energy Performance Certificate rates a home A (best) to G (worst) for energy "
    "efficiency, based on its fabric and heating, not how it's used day to day.",
    "rofrs": "Risk of Flooding from Rivers and Sea: the Environment Agency's official flood "
    "likelihood band for a location (very low, low, medium or high).",
    "u-value": "A measure of how much heat escapes through a wall, roof or window. Lower is "
    "better insulated.",
    "scop": "Seasonal Coefficient of Performance: how many units of heat a heat pump produces "
    "per unit of electricity it uses, averaged over a year. Higher is more efficient.",
    "fabric first": "The principle of insulating and draught-proofing a home well before "
    "adding new heating or generation, so less energy is needed overall.",
    "subsidence": "Ground movement, often linked to clay soil drying and shrinking, that can "
    "damage a building's foundations.",
    "overheating": "The risk of a home becoming uncomfortably or dangerously hot, which is "
    "rising with climate change, especially for top-floor flats and south-facing rooms.",
    "surface water flooding": "Flooding from heavy rainfall overwhelming drains, rather than "
    "a river or the sea rising.",
    "resilience score": "This passport's 0-100 score across flood, heat, storm, subsidence "
    "and carbon, each scored against official or modelled data.",
    "retrofit": "Upgrading an existing home's fabric, heating or generation, as opposed to "
    "features built in when it was constructed.",
}

TEMPLATE_SUGGESTED = [
    "What's my biggest risk?",
    "What's the cheapest way to cut my bills?",
    "What should I do next?",
]
