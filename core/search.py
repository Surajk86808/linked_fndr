# core/search.py  -  Safe LinkedIn people search with pagination

import random
import re
from pathlib import Path
from urllib.parse import quote

from selenium import webdriver
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import config
from utils.human import delay_page_load, delay_pages, human_scroll, short_pause
from utils.logger import log
from utils.seen_urls import SeenUrls

_DEBUG_CAPTURED = False

# Build flat geoUrn map from discovered locations in config.GEO_LOCATIONS.
# Falls back to hardcoded country-level IDs when geoUrns.json not found.
_COUNTRY_URNS = {
    "India":          "103644278",
    "United States":  "103644286",
    "United Kingdom": "101165590",
    "Japan":          "101355337",
    "Germany":        "101282230",
    "Australia":      "101452733",
    "Canada":         "101174742",
    "Singapore":      "102454443",
    "UAE":            "104305776",
    "Brazil":         "106057199",
}

GEO_URN_MAP: dict = {}
if config.GEO_LOCATIONS:
    for _country_data in config.GEO_LOCATIONS.values():
        for _city_locs in _country_data.values():
            for _loc in _city_locs:
                GEO_URN_MAP[_loc["name"]] = _loc["geoUrn"]
else:
    GEO_URN_MAP = dict(_COUNTRY_URNS)


def _build_url(keyword: str, page: int = 1, geo_urn: str = None) -> str:
    kw = quote(keyword)
    url = (
        f"https://www.linkedin.com/search/results/people/"
        f"?keywords={kw}"
        f"&origin=FACETED_SEARCH"
        f"&spellCorrectionEnabled=true"
        f"&page={page}"
    )
    if geo_urn:
        url += f"&geoUrn=%5B%22{geo_urn}%22%5D"
    return url


def _extract_urls_from_page(driver: webdriver.Chrome) -> list[str]:
    """Pull all /in/ profile links from the current search results page."""
    urls = []
    seen = set()
    selectors = [
        "a.app-aware-link[href*='/in/']",
        "span.entity-result__title-text a[href*='/in/']",
        "a[href*='linkedin.com/in/']",
        "a[href*='/in/']",
    ]

    for sel in selectors:
        try:
            anchors = driver.find_elements(By.CSS_SELECTOR, sel)
            for anchor in anchors:
                try:
                    href = anchor.get_attribute("href") or ""
                    if "/in/" not in href:
                        continue
                    clean = href.split("?")[0].rstrip("/")
                    if clean not in seen:
                        urls.append(clean)
                        seen.add(clean)
                except StaleElementReferenceException:
                    continue
        except Exception:
            continue

    if not urls:
        try:
            matches = re.findall(r"https://www\.linkedin\.com/in/[^\"'?&<]+", driver.page_source)
            for href in matches:
                clean = href.rstrip("/")
                if clean not in seen:
                    urls.append(clean)
                    seen.add(clean)
        except Exception:
            pass

    return urls


def _has_next_page(driver: webdriver.Chrome) -> bool:
    """Check if a next-page button exists and is enabled."""
    selectors = [
        "button[aria-label='Next']",
        "button[aria-label*='Next']",
        "button.artdeco-pagination__button--next",
    ]
    for sel in selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            return btn.is_enabled()
        except NoSuchElementException:
            continue
    return False


def _click_next(driver: webdriver.Chrome) -> bool:
    """Click the next pagination button. Returns False if unavailable."""
    selectors = [
        "button[aria-label='Next']",
        "button[aria-label*='Next']",
        "button.artdeco-pagination__button--next",
    ]
    for sel in selectors:
        try:
            btn = WebDriverWait(driver, 6).until(lambda d: d.find_element(By.CSS_SELECTOR, sel))
            if not btn.is_enabled():
                continue
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            short_pause()
            btn.click()
            delay_pages()
            return True
        except Exception:
            continue
    return False


def _hit_wall(driver: webdriver.Chrome) -> bool:
    """Detect if LinkedIn has shown an auth wall or rate-limit page."""
    url = driver.current_url.lower()
    html = driver.page_source.lower()
    return (
        any(x in url for x in ["authwall", "checkpoint", "challenge"])
        or "let's do a quick security check" in html
        or "verify your identity" in html
    )


def _save_debug_artifacts(driver: webdriver.Chrome, keyword: str, page: int):
    global _DEBUG_CAPTURED
    if _DEBUG_CAPTURED:
        return

    safe_keyword = re.sub(r"[^a-zA-Z0-9_-]+", "_", keyword).strip("_") or "keyword"
    html_path = Path(f"debug_search_{safe_keyword}_p{page}.html")
    png_path = Path(f"debug_search_{safe_keyword}_p{page}.png")

    try:
        html_path.write_text(driver.page_source, encoding="utf-8")
        driver.save_screenshot(str(png_path))
        log(f"  Saved debug HTML: {html_path}", "INFO")
        log(f"  Saved screenshot: {png_path}", "INFO")
        _DEBUG_CAPTURED = True
    except Exception as error:
        log(f"  Failed to save debug artifacts: {error}", "WARN")


def _wait_for_search_page(driver: webdriver.Chrome, page: int) -> bool:
    """Wait until the page contains enough search content to parse."""
    try:
        WebDriverWait(driver, 12).until(
            lambda d: (
                bool(d.find_elements(By.CSS_SELECTOR, "div.search-results-container"))
                or bool(d.find_elements(By.CSS_SELECTOR, "ul.reusable-search__entity-result-list"))
                or bool(d.find_elements(By.CSS_SELECTOR, "a[href*='/in/']"))
                or "no results" in d.page_source.lower()
                or "no matching results" in d.page_source.lower()
            )
        )
        return True
    except TimeoutException:
        log(f"  Page {page}: Search results did not become parsable.", "WARN")
        return False


def search_profiles(
    driver: webdriver.Chrome,
    keyword: str,
    seen: SeenUrls,
    geo_urn: str = None,
    location_label: str = None,
) -> list[str]:
    """Search LinkedIn for a keyword with optional city-level geoUrn filtering."""
    label = f"'{keyword}'" + (f" | {location_label or geo_urn}" if (location_label or geo_urn) else "")
    log(f"Searching: {label}", "SCRAPE")
    collected = []
    page = 1

    while True:
        url = _build_url(keyword, page, geo_urn)
        try:
            driver.get(url)
            delay_page_load()
        except (InvalidSessionIdException, WebDriverException) as error:
            log(f"Search browser session failed on page {page}: {error}", "ERROR")
            break

        if _hit_wall(driver):
            log("Auth wall detected - stopping search for this keyword.", "WARN")
            break

        page_ready = _wait_for_search_page(driver, page)
        if not page_ready:
            log(f"  Debug title: {driver.title[:80]}", "INFO")
            log(f"  Debug URL  : {driver.current_url}", "INFO")

        human_scroll(driver)

        page_urls = _extract_urls_from_page(driver)
        if not page_urls:
            _save_debug_artifacts(driver, keyword, page)
            log(f"  Page {page}: No profiles found. End of results.", "INFO")
            break

        new_count = 0
        for profile_url in page_urls:
            if profile_url not in collected and not seen.seen(profile_url):
                collected.append(profile_url)
                new_count += 1

        log(f"  Page {page}: +{new_count} new profiles  ({len(collected)} total)")

        if not _has_next_page(driver):
            log(f"  No more pages for {label}.")
            break

        if random.random() < 0.08:
            log("  Skipping one page (human behaviour)...", "INFO")
            page += 2
        else:
            page += 1

        if not _click_next(driver):
            log(f"  Pagination unavailable for {label}.", "INFO")
            break

    log(f"Collected {len(collected)} profiles for {label}", "OK")
    return collected
