"""Removes UK postcodes and email addresses from a user's typed message before it goes
anywhere near the model or a log line (CONTRACT.md §6 rule 2)."""

from app.studio.features.s19_concierge.config import EMAIL_PATTERN, UK_POSTCODE_PATTERN


def scrub_personal(text: str) -> str:
    text = EMAIL_PATTERN.sub("[removed]", text)
    return UK_POSTCODE_PATTERN.sub("[removed]", text)
