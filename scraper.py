# core/scraper.py  —  Full LinkedIn profile scraper
#
# Visits a single profile URL and extracts all fields.
# Returns a populated Lead dataclass or None if filtered out.

import re
from dataclasses import dataclass
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, StaleElementReferenceException, TimeoutException
)

import config
from human import human_scroll, delay_page_load, delay_contact_modal, short_pause
from date_parser import parse_role_date, days_ago_label
from scorer import score_lead
from logger import log


# ══════════════════════════════════════════════════════════════════
#  Lead data model
# ══════════════════════════════════════════════════════════════════

@dataclass
class Lead:
    # Identity
    name:              str = ""
    headline:          str = ""
    location:          str = ""
    linkedin_url:      str = ""
    connections:       str = ""

    # Current role
    current_title:     str = ""
    company:           str = ""
    role_start_date:   str = ""
    role_start_days:   int = 9999
    role_recency_label:str = ""

    # Company
    website:           str = ""
    has_website:       str = "NO"
    company_size:      str = ""

    # Profile depth
    about:             str = ""
    skills:            str = ""
    education:         str = ""

    # Scoring
    score:             int = 0
    score_breakdown:   str = ""
    priority:          str = ""

    # Meta
    scraped_date:      str = ""
    keyword_matched:   str = ""


# ══════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════

def _safe_text(driver, by, sel, default="") -> str:
    try:
        return driver.find_element(by, sel).text.strip()
    except NoSuchElementException:
        return default


def _all_texts(driver, by, sel) -> list[str]:
    try:
        return [el.text.strip() for el in driver.find_elements(by, sel) if el.text.strip()]
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════
#  Section scrapers
# ══════════════════════════════════════════════════════════════════

def _scrape_basic(driver: webdriver.Chrome, lead: Lead):
    """Name, headline, location, connection count."""
    lead.name = _safe_text(driver, By.CSS_SELECTOR, "h1.text-heading-xlarge")

    lead.headline = _safe_text(
        driver, By.CSS_SELECTOR, "div.text-body-medium.break-words"
    )

    lead.location = _safe_text(
        driver, By.CSS_SELECTOR,
        "span.text-body-small.inline.t-black--light.break-words"
    )

    # Connections — "500+ connections", "2nd", etc.
    for sel in [
        "span.t-bold ~ span.t-normal",
        "li.text-body-small span",
    ]:
        val = _safe_text(driver, By.CSS_SELECTOR, sel)
        if "connection" in val.lower():
            lead.connections = val
            break


def _scrape_about(driver: webdriver.Chrome, lead: Lead):
    """First 400 chars of the About section."""
    about = _safe_text(
        driver, By.CSS_SELECTOR,
        "div.display-flex.ph5.pv3 span[aria-hidden='true']"
    )
    if not about:
        # Fallback selector
        about = _safe_text(
            driver, By.XPATH,
            "//section[.//span[text()='About']]//span[@aria-hidden='true']"
        )
    lead.about = about[:400]


def _scrape_experience(driver: webdriver.Chrome, lead: Lead):
    """
    Extract the current (first) experience entry.
    Applies the date recency filter — returns False to signal skip.
    """
    # Try multiple selector strategies
    selectors = [
        "section[data-section='experience'] li.artdeco-list__item",
        "#experience ~ div li.artdeco-list__item",
        "//section[.//span[text()='Experience']]//li[contains(@class,'artdeco-list__item')]",
    ]

    items = []
    for sel in selectors:
        try:
            if sel.startswith("//"):
                items = driver.find_elements(By.XPATH, sel)
            else:
                items = driver.find_elements(By.CSS_SELECTOR, sel)
            if items:
                break
        except Exception:
            continue

    for item in items[:3]:
        try:
            spans = item.find_elements(By.CSS_SELECTOR, "span[aria-hidden='true']")
            texts = [s.text.strip() for s in spans if s.text.strip()]

            if not texts:
                continue

            title   = texts[0] if len(texts) > 0 else ""
            company = texts[1] if len(texts) > 1 else ""

            # Find date string in this entry
            date_str = ""
            for t in texts:
                if re.search(r"\d{4}", t) or "present" in t.lower():
                    date_str = t
                    break

            if title:
                lead.current_title   = title
                lead.company         = company
                lead.role_start_date = date_str

                if date_str:
                    is_recent, days_ago = parse_role_date(date_str)
                    lead.role_start_days    = days_ago
                    lead.role_recency_label = days_ago_label(days_ago)
                break

        except (StaleElementReferenceException, IndexError):
            continue

    # Fallback — use headline as title
    if not lead.current_title:
        lead.current_title = lead.headline


def _scrape_website(driver: webdriver.Chrome, lead: Lead, profile_url: str):
    """Open the contact-info overlay and extract company website."""
    try:
        contact_url = profile_url.rstrip("/") + "/overlay/contact-info/"
        driver.get(contact_url)
        delay_contact_modal()

        links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
        for link in links:
            href = (link.get_attribute("href") or "").strip()
            if (
                href.startswith("http")
                and "linkedin.com" not in href
                and "mailto:"      not in href
                and len(href)       > 10
            ):
                lead.website     = href
                lead.has_website = "YES"
                break

        driver.back()
        delay_page_load()

    except Exception:
        lead.has_website = "NO"


def _scrape_skills(driver: webdriver.Chrome, lead: Lead):
    """Top 5 skills as comma-separated string."""
    selectors = [
        "section[data-section='skills'] span[aria-hidden='true']",
        "#skills ~ div span[aria-hidden='true']",
    ]
    skills = []
    seen   = set()

    for sel in selectors:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                t = el.text.strip()
                if t and t not in seen and len(t) > 2 and not t.isdigit():
                    skills.append(t)
                    seen.add(t)
                if len(skills) >= 5:
                    break
        except Exception:
            continue
        if skills:
            break

    lead.skills = ", ".join(skills)


def _scrape_education(driver: webdriver.Chrome, lead: Lead):
    """Most recent educational institution."""
    selectors = [
        "section[data-section='education'] li span[aria-hidden='true']",
        "#education ~ div li span[aria-hidden='true']",
    ]
    for sel in selectors:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                t = el.text.strip()
                if t and len(t) > 3:
                    lead.education = t
                    return
        except Exception:
            continue


# ══════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════

def scrape_profile(
    driver:  webdriver.Chrome,
    url:     str,
    keyword: str,
) -> Lead | None:
    """
    Visit a LinkedIn profile and extract all fields.

    Returns:
        Populated Lead   — if profile passes the date filter
        None             — if role started outside RECENCY_DAYS window
                           or if page failed to load
    """
    log(f"  {url.split('/in/')[-1][:40]}", "SCRAPE")
    driver.get(url)
    delay_page_load()

    # Progressive scroll to trigger lazy-loaded sections
    human_scroll(driver, steps=config.SCROLL_STEPS)
    short_pause()

    lead = Lead(
        linkedin_url    = url,
        scraped_date    = datetime.now().strftime("%Y-%m-%d"),
        keyword_matched = keyword,
    )

    _scrape_basic(driver, lead)
    _scrape_about(driver, lead)
    _scrape_experience(driver, lead)

    # ── Date recency filter ───────────────────────────────────────
    if lead.role_start_date:
        is_recent, days_ago = parse_role_date(lead.role_start_date)
        if not is_recent and days_ago > config.RECENCY_DAYS:
            log(
                f"  DATE FILTERED — role started {days_ago}d ago"
                f" ({lead.role_start_date})",
                "DATE"
            )
            return None

    _scrape_website(driver, lead, url)
    _scrape_skills(driver, lead)
    _scrape_education(driver, lead)

    # ── Score ─────────────────────────────────────────────────────
    result            = score_lead(
        has_website  = lead.has_website,
        days_ago     = lead.role_start_days,
        title        = lead.current_title,
        company_size = lead.company_size,
        location     = lead.location,
    )
    lead.score          = result.total
    lead.score_breakdown= result.breakdown
    lead.priority       = result.priority

    log(
        f"  {(lead.name or 'Unknown')[:25]:<25} | "
        f"{lead.current_title[:28]:<28} | "
        f"Score {lead.score:>3} | {lead.priority}",
        "OK"
    )

    return lead
