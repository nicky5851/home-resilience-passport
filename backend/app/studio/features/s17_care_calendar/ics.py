"""A hand-written RFC 5545 writer (docs/studio/N_20_function.md §S17 Algorithm 3): CRLF line
ends, 75-octet folding, a stable UID per task, and a one-day-before reminder. No dependency."""

from datetime import date, datetime


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold_line(line: str) -> str:
    """RFC 5545 §3.1: no line (including the CRLF) may exceed 75 octets; a continuation line
    starts with a single space, which counts towards that line's own 75-octet limit."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    pieces: list[bytes] = []
    pos = 0
    limit = 75
    while pos < len(raw):
        end = min(pos + limit, len(raw))
        while end < len(raw) and (raw[end] & 0xC0) == 0x80:  # don't split a multi-byte char
            end -= 1
        pieces.append(raw[pos:end])
        pos = end
        limit = 74  # continuation lines carry a leading space inside the same 75-octet budget
    return "\r\n ".join(p.decode("utf-8") for p in pieces)


def write_ics(
    tasks: list[dict], home_hash: str, now: datetime, calendar_name: str = "Home Care Calendar"
) -> str:
    """`tasks`: each `{id, title, why, month, day}`."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Home Resilience Passport//Care Calendar//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_escape(calendar_name)}",
    ]
    for task in tasks:
        start = date(now.year, task["month"], task["day"])
        lines += [
            "BEGIN:VEVENT",
            f"UID:{task['id']}-{home_hash}@hrp",
            f"DTSTAMP:{now.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
            "RRULE:FREQ=YEARLY",
            f"SUMMARY:{_escape(task['title'])}",
            f"DESCRIPTION:{_escape(task['why'])}",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_escape(task['title'])}",
            "TRIGGER:-P1D",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold_line(line) for line in lines) + "\r\n"
