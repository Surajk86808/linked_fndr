# core/scraper.py  -  Full LinkedIn profile scraper

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import config
from utils.date_parser import days_ago_label, parse_role_date
from utils.human import delay_contact_modal, delay_page_load, human_scroll, short_pause
from utils.logger import log
from utils.scorer import score_lead


@dataclass
class Lead:
    name: str = ""
    headline: str = ""
    location: str = ""
    linkedin_url: str = ""
    connections: str = ""
    current_title: str = ""
    company: str = ""
    role_start_date: str = ""
    role_start_days: int = 9999
    role_recency_label: str = ""
    website: str = ""
    has_website: str = "NO"
    company_size: str = ""
    about: str = ""
    skills: str = ""
    education: str = ""
    score: int = 0
    score_breakdown: str = ""
    priority: str = ""
    scraped_date: str = ""
    keyword_matched: str = ""
    country: str = ""


def _safe_text(driver, by, sel, default="") -> str:
    try:
        return driver.find_element(by, sel).text.strip()
    except NoSuchElementException:
        return default


def _scrape_basic(driver: webdriver.Chrome, lead: Lead):
    lead.name = _safe_text(driver, By.CSS_SELECTOR, "h1.text-heading-xlarge")
    lead.headline = _safe_text(driver, By.CSS_SELECTOR, "div.text-body-medium.break-words")
    lead.location = _safe_text(
        driver,
        By.CSS_SELECTOR,
        "span.text-body-small.inline.t-black--light.break-words",
    )

    for sel in ["span.t-bold ~ span.t-normal", "li.text-body-small span"]:
        val = _safe_text(driver, By.CSS_SELECTOR, sel)
        if "connection" in val.lower():
            lead.connections = val
            break


def _scrape_about(driver: webdriver.Chrome, lead: Lead):
    about = _safe_text(
        driver,
        By.CSS_SELECTOR,
        "div.display-flex.ph5.pv3 span[aria-hidden='true']",
    )
    if not about:
        about = _safe_text(
            driver,
            By.XPATH,
            "//section[.//span[text()='About']]//span[@aria-hidden='true']",
        )
    lead.about = about[:400]


def _scrape_experience(driver: webdriver.Chrome, lead: Lead):
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
            texts = [span.text.strip() for span in spans if span.text.strip()]
            if not texts:
                continue

            title = texts[0] if len(texts) > 0 else ""
            company = texts[1] if len(texts) > 1 else ""

            date_str = ""
            for text in texts:
                if re.search(r"\d{4}", text) or "present" in text.lower():
                    date_str = text
                    break

            if title:
                lead.current_title = title
                lead.company = company
                lead.role_start_date = date_str

                if date_str:
                    _is_recent, days_ago = parse_role_date(date_str)
                    lead.role_start_days = days_ago
                    lead.role_recency_label = days_ago_label(days_ago)
                break
        except (StaleElementReferenceException, IndexError):
            continue

    if not lead.current_title:
        lead.current_title = lead.headline


def _scrape_website(driver: webdriver.Chrome, lead: Lead, profile_url: str):
    """Click the contact-info button and extract company website from the modal."""
    try:
        contact_selectors = [
            "a[href*='contact-info']",
            "a#top-card-text-details-contact-info",
            "a.ember-view[href*='overlay/contact-info']",
        ]
        contact_link = None
        for sel in contact_selectors:
            try:
                contact_link = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                break
            except Exception:
                continue

        if not contact_link:
            lead.has_website = "Unknown"
            return

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", contact_link)
        short_pause()
        contact_link.click()
        delay_contact_modal()

        modal_links = driver.find_elements(
            By.CSS_SELECTOR,
            "div.pv-contact-info__contact-type a[href], section.pv-contact-info a[href]",
        )
        for link in modal_links:
            href = (link.get_attribute("href") or "").strip()
            if (
                href.startswith("http")
                and "linkedin.com" not in href
                and "mailto:" not in href
                and len(href) > 10
            ):
                lead.website = href
                lead.has_website = "YES"
                break

        from selenium.webdriver.common.keys import Keys

        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        short_pause()
    except Exception:
        lead.has_website = "Unknown"


def _scrape_skills(driver: webdriver.Chrome, lead: Lead):
    selectors = [
        "section[data-section='skills'] span[aria-hidden='true']",
        "#skills ~ div span[aria-hidden='true']",
    ]
    skills = []
    seen = set()

    for sel in selectors:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                text = el.text.strip()
                if text and text not in seen and len(text) > 2 and not text.isdigit():
                    skills.append(text)
                    seen.add(text)
                if len(skills) >= 5:
                    break
        except Exception:
            continue
        if skills:
            break

    lead.skills = ", ".join(skills)


def _scrape_education(driver: webdriver.Chrome, lead: Lead):
    selectors = [
        "section[data-section='education'] li span[aria-hidden='true']",
        "#education ~ div li span[aria-hidden='true']",
    ]
    for sel in selectors:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                text = el.text.strip()
                if text and len(text) > 3:
                    lead.education = text
                    return
        except Exception:
            continue


def scrape_profile(
    driver: webdriver.Chrome,
    url: str,
    keyword: str,
    country: str = "",
) -> Optional[Lead]:
    log(f"  {url.split('/in/')[-1][:40]}", "SCRAPE")
    driver.get(url)
    delay_page_load()

    human_scroll(driver, steps=config.SCROLL_STEPS)
    short_pause()

    lead = Lead(
        linkedin_url=url,
        scraped_date=datetime.now().strftime("%Y-%m-%d"),
        keyword_matched=keyword,
        country=country,
    )

    _scrape_basic(driver, lead)
    _scrape_about(driver, lead)
    _scrape_experience(driver, lead)

    if lead.role_start_date:
        is_recent, days_ago = parse_role_date(lead.role_start_date)
        if days_ago != 9999 and not is_recent:
            log(
                f"  DATE FILTERED - role started {days_ago}d ago"
                f" ({lead.role_start_date})",
                "DATE",
            )
            return None

    _scrape_website(driver, lead, url)
    _scrape_skills(driver, lead)
    _scrape_education(driver, lead)

    result = score_lead(
        has_website=lead.has_website,
        days_ago=lead.role_start_days,
        title=lead.current_title,
        company_size=lead.company_size,
        location=lead.location,
    )
    lead.score = result.total
    lead.score_breakdown = result.breakdown
    lead.priority = result.priority

    log(
        f"  {(lead.name or 'Unknown')[:25]:<25} | "
        f"{lead.current_title[:28]:<28} | "
        f"Score {lead.score:>3} | {lead.priority}",
        "OK",
    )

    return lead
