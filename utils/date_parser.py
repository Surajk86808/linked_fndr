# utils/date_parser.py  -  Parse LinkedIn role dates, check recency

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

import config

MONTH_MAP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def parse_role_date(date_str: str) -> Tuple[bool, int]:
    """Parse a LinkedIn experience date string and determine recency."""
    if not date_str:
        return False, 9999

    raw = date_str.lower().strip()
    now = datetime.now()
    cutoff = now - timedelta(days=config.RECENCY_DAYS)
    start_part = re.split(r"[\u2013\-\u00b7]", raw)[0].strip()

    match = re.search(r"([a-z]{3,9})\s+(\d{4})", start_part)
    if match:
        month_str = match.group(1)[:3]
        month = MONTH_MAP.get(month_str, 0)
        year = int(match.group(2))
        if month:
            role_date = _safe_date(year, month)
            if role_date:
                days_ago = (now - role_date).days
                return role_date >= cutoff, max(days_ago, 0)

    match = re.search(r"(\d{4})", start_part)
    if match:
        year = int(match.group(1))
        role_date = _safe_date(year, 1)
        if role_date:
            days_ago = (now - role_date).days
            return role_date >= cutoff, max(days_ago, 0)

    return False, 9999


def days_ago_label(days: int) -> str:
    if days == 9999:
        return "Unknown"
    if days <= 30:
        return f"{days}d ago"
    if days <= 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}yr ago"


def _safe_date(year: int, month: int) -> Optional[datetime]:
    try:
        return datetime(year, month, 1)
    except ValueError:
        return None
