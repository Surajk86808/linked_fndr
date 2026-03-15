# utils/date_parser.py  —  Parse LinkedIn role dates, check recency

import re
from datetime import datetime, timedelta
from typing import Tuple

import config

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_role_date(date_str: str) -> Tuple[bool, int]:
    """
    Parse a LinkedIn experience date string and determine if the role
    started within config.RECENCY_DAYS.

    Handles formats like:
        "Jan 2025"
        "Jan 2025 – Present"
        "January 2025 - Present"
        "2025 – Present"
        "Jan 2025 · 3 mos"

    Returns:
        (is_recent: bool, days_ago: int)
        is_recent = True  → role started within RECENCY_DAYS
        days_ago  = 9999  → could not parse date
    """
    if not date_str:
        return False, 9999

    raw   = date_str.lower().strip()
    now   = datetime.now()
    cutoff = now - timedelta(days=config.RECENCY_DAYS)

    # Take only the start portion (before "–", "-", or "·")
    start_part = re.split(r"[–\-·]", raw)[0].strip()

    # ── Try "Mon YYYY" e.g. "jan 2025" ───────────────────────────
    m = re.search(r"([a-z]{3,9})\s+(\d{4})", start_part)
    if m:
        month_str = m.group(1)[:3]
        month     = MONTH_MAP.get(month_str, 0)
        year      = int(m.group(2))
        if month:
            role_date = _safe_date(year, month)
            if role_date:
                days_ago = (now - role_date).days
                return role_date >= cutoff, max(days_ago, 0)

    # ── Try just "YYYY" ───────────────────────────────────────────
    m = re.search(r"(\d{4})", start_part)
    if m:
        year = int(m.group(1))
        role_date = _safe_date(year, 1)
        if role_date:
            days_ago = (now - role_date).days
            return role_date >= cutoff, max(days_ago, 0)

    return False, 9999


def days_ago_label(days: int) -> str:
    """Human-readable label for days_ago value."""
    if days == 9999:
        return "Unknown"
    if days <= 30:
        return f"{days}d ago"
    if days <= 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}yr ago"


def _safe_date(year: int, month: int) -> datetime | None:
    try:
        return datetime(year, month, 1)
    except ValueError:
        return None
