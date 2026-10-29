"""Number guard (docs/studio/N_20_function.md §S19 Algorithm 3): every £/%/kWh/kg/points
figure in the answer must appear, verbatim, in a tool result from this turn."""

import re

from app.studio.features.s19_concierge.config import NUMBER_PATTERN

_DIGITS = re.compile(r"[\d,]*\d(?:\.\d+)?")


def _normalise(number: str) -> str:
    """Strip commas, units and spacing so "£1,200" and "1200" compare equal."""
    digits = _DIGITS.findall(number)
    if not digits:
        return number
    value = digits[0].replace(",", "")
    return value.rstrip("0").rstrip(".") if "." in value else value


def extract_numbers(text: str) -> list[str]:
    return NUMBER_PATTERN.findall(text)


def numbers_supported(answer: str, tool_outputs_text: str) -> bool:
    found = extract_numbers(answer)
    if not found:
        return True
    haystack_numbers = {_normalise(n) for n in _DIGITS.findall(tool_outputs_text)}
    return all(_normalise(n) in haystack_numbers for n in found)
