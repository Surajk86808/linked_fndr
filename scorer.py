# utils/scorer.py  —  NexviaTech Lead Scoring (0–100)
#
# Five independent dimensions scored and summed.
# Weights reflect what actually drives conversion for NexviaTech:
# website absence matters most, recency second, then title/size/location.

from dataclasses import dataclass
from typing import Tuple
import config


@dataclass
class ScoreResult:
    total:     int
    priority:  str
    breakdown: str   # Human-readable breakdown of points


# ══════════════════════════════════════════════════════════════════
#  Dimension weights
# ══════════════════════════════════════════════════════════════════

def _score_website(has_website: str) -> Tuple[int, str]:
    """35 pts max — No website is the primary buying signal."""
    if has_website == "NO":
        return 35, "No website +35"
    if has_website == "YES":
        return 5,  "Has website +5"
    return 15, "Website unknown +15"


def _score_recency(days_ago: int) -> Tuple[int, str]:
    """25 pts max — Fresher role = more likely to need a web presence."""
    if 0 < days_ago <= 30:
        return 25, "Role <30d +25"
    if 30 < days_ago <= 60:
        return 20, "Role 30-60d +20"
    if 60 < days_ago <= 90:
        return 15, "Role 60-90d +15"
    if 90 < days_ago <= 180:
        return 8,  "Role 3-6mo +8"
    return 0, "Role >6mo +0"


def _score_title(title: str) -> Tuple[int, str]:
    """20 pts max — Founder beats Co-Founder beats Director."""
    t = title.lower()
    if "founder & ceo" in t or "founder/ceo" in t or "founder-ceo" in t:
        return 20, "Founder+CEO +20"
    if t.startswith("founder"):
        return 18, "Founder +18"
    if "co-founder" in t or "cofounder" in t:
        return 15, "Co-Founder +15"
    if "founding" in t:
        return 12, "Founding role +12"
    return 5, "Other title +5"


def _score_company_size(size: str) -> Tuple[int, str]:
    """10 pts max — Solo/tiny companies have no internal web team."""
    s = size.lower()
    if any(x in s for x in ["self-employed", "1 employee", "freelance", "sole"]):
        return 10, "Solo/self-employed +10"
    if "2-10" in s:
        return 7, "2-10 employees +7"
    if "11-50" in s:
        return 4, "11-50 employees +4"
    if not s:
        return 5, "Size unknown +5"
    return 2, "50+ employees +2"


def _score_location(location: str) -> Tuple[int, str]:
    """10 pts max — US = premium pricing, India = volume."""
    loc = location.lower()
    us_cities = [
        "united states", "usa", "u.s.", "miami", "new york", "los angeles",
        "san francisco", "chicago", "houston", "dallas", "seattle", "austin",
    ]
    india_cities = [
        "india", "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad",
        "pune", "chennai", "kolkata", "ahmedabad", "noida", "gurugram",
    ]
    if any(x in loc for x in us_cities):
        return 10, "US location +10"
    if any(x in loc for x in india_cities):
        return 8, "India location +8"
    if loc:
        return 4, "Other location +4"
    return 3, "Location unknown +3"


# ══════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════

def score_lead(
    has_website: str,
    days_ago:    int,
    title:       str,
    company_size:str,
    location:    str,
) -> ScoreResult:
    """
    Score a lead across all five dimensions.

    Args:
        has_website:  "YES" | "NO" | "Unknown"
        days_ago:     int — days since role started (9999 = unknown)
        title:        current job title string
        company_size: e.g. "2-10 employees" or ""
        location:     location string from profile

    Returns:
        ScoreResult with total (0–100), priority, and breakdown string
    """
    scores = [
        _score_website(has_website),
        _score_recency(days_ago),
        _score_title(title),
        _score_company_size(company_size),
        _score_location(location),
    ]

    total     = min(sum(s for s, _ in scores), 100)
    breakdown = " | ".join(label for _, label in scores)
    priority  = _priority(total)

    return ScoreResult(total=total, priority=priority, breakdown=breakdown)


def _priority(score: int) -> str:
    if score >= config.SCORE_HIGH:   return "HIGH"
    if score >= config.SCORE_MEDIUM: return "MEDIUM"
    return "LOW"
