"""
NEXVIATECH - LinkedIn Founder Scraper v2.0
Run: python main.py
"""

import random
import sys
import time

import config
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException

from core.browser import create_driver
from core.login import login
from core.scraper import scrape_profile
from core.search import search_profiles
from data.xlsx_writer import add_summary_sheet, init_xlsx, save_lead
from utils.checkpoint import Checkpoint
from utils.human import delay_keywords, delay_profiles, human_scroll, wiggle_mouse
from utils.logger import Dashboard, log
from utils.seen_urls import SeenUrls


def validate_config():
    if "your_email" in config.LINKEDIN_EMAIL:
        print("\nOpen config.py and set your LINKEDIN_EMAIL and LINKEDIN_PASSWORD.\n")
        sys.exit(1)


def print_banner():
    using_geo = bool(config.GEO_LOCATIONS)
    mode      = "city-level geoUrns" if using_geo else "country-level (run discover_geoUrns.py for more)"
    print("\n" + "=" * 62)
    print("  NEXVIATECH - LinkedIn Founder Scraper v2.0")
    print(f"  Countries  : {len(config.TARGET_COUNTRIES)} countries")
    print(f"  Titles     : {', '.join(config.FOUNDER_TITLES)}")
    print(f"  Location   : {mode}")
    print(f"  Recency    : last {config.RECENCY_DAYS} days only")
    print(f"  Daily cap  : {config.DAILY_CAP} profiles")
    print(f"  Output     : {config.OUTPUT_XLSX}")
    print("=" * 62 + "\n")


def ask_resume(checkpoint: Checkpoint) -> bool:
    if not checkpoint.exists():
        return False
    total = checkpoint.total()
    print(f"Checkpoint found - {total} profiles processed in a previous run.")
    choice = input("    (R) Resume  /  (N) Start fresh  -> ").strip().upper()
    if choice == "N":
        checkpoint.reset()
        log("Starting fresh.", "INFO")
        return False
    log(f"Resuming from checkpoint ({total} already done).", "OK")
    return True


def generate_search_tasks() -> list:
    """
    Generate (title, location_name, geo_urn, country) tuples.

    When geoUrns.json exists: produces city-level tasks (many more results).
    Fallback: uses TARGET_COUNTRIES with country-level geoUrns.
    """
    tasks = []

    if config.GEO_LOCATIONS:
        for country, cities in config.GEO_LOCATIONS.items():
            for city, locations in cities.items():
                for location in locations:
                    for title in config.FOUNDER_TITLES:
                        tasks.append((
                            title,
                            location["name"],
                            location["geoUrn"],
                            country,
                        ))
    else:
        # Fallback: country-level search
        from core.search import _COUNTRY_URNS
        for country in config.TARGET_COUNTRIES:
            for title in config.FOUNDER_TITLES:
                tasks.append((title, country, _COUNTRY_URNS.get(country), country))

    return tasks


class ProxyPool:
    def __init__(self):
        self._pool = list(config.PROXIES)
        self._idx  = 0

    def current(self):
        return self._pool[self._idx % len(self._pool)] if self._pool else None

    def rotate(self):
        if self._pool:
            self._idx += 1
            log(f"Proxy rotated -> {self.current()}", "INFO")


def run():
    validate_config()
    print_banner()

    checkpoint = Checkpoint()
    seen       = SeenUrls()
    dash       = Dashboard(print_every=5)
    proxies    = ProxyPool()

    ask_resume(checkpoint)
    init_xlsx()

    driver = create_driver(proxy=proxies.current())
    profiles_this_session = 0

    try:
        if not login(driver):
            log("Login failed - aborting.", "ERROR")
            return

        tasks = generate_search_tasks()
        random.shuffle(tasks)
        log(f"Total search tasks: {len(tasks)}", "INFO")

        for title, location_name, geo_urn, country in tasks:
            if dash.total >= config.DAILY_CAP:
                log(f"Daily cap ({config.DAILY_CAP}) reached. Stopping.", "WARN")
                break

            log(f"\n{'-' * 50}")
            log(f"Keyword: '{title}' | Location: '{location_name}'")
            log(f"All-time seen: {seen.count()} | Session: {profiles_this_session}")
            log(f"{'-' * 50}")

            profile_urls = search_profiles(
                driver, title, seen,
                geo_urn=geo_urn,
                location_label=location_name,
            )

            for url in profile_urls:
                if dash.total >= config.DAILY_CAP:
                    break

                if checkpoint.already_done(url):
                    log(f"  Checkpoint skip: ...{url[-30:]}", "SKIP")
                    dash.skip()
                    continue

                try:
                    lead = scrape_profile(driver, url, title, country)

                    if lead and lead.name:
                        save_lead(lead, country=country)
                        checkpoint.mark_done(url)
                        seen.add(url)
                        dash.record(lead.priority)
                        profiles_this_session += 1

                        # Human break every 10 profiles
                        if profiles_this_session % 10 == 0:
                            pause_mins = random.uniform(2.0, 5.0)
                            log(
                                f"  [{profiles_this_session} scraped] "
                                f"Human break: {pause_mins:.1f} min pause...",
                                "WARN",
                            )
                            time.sleep(pause_mins * 60)
                            try:
                                wiggle_mouse(driver)
                                human_scroll(driver, steps=2)
                            except Exception:
                                pass
                    else:
                        checkpoint.mark_done(url)
                        seen.add(url)
                        if lead is None:
                            dash.date_filter()
                        else:
                            dash.skip()

                except Exception as error:
                    log(f"  Error scraping {url}: {error}", "ERROR")
                    dash.error()

                if random.random() < config.PROXY_ROTATE_CHANCE:
                    proxies.rotate()

                delay_profiles()

            log(f"\n'{title}' / '{location_name}' complete. Taking a break...")
            delay_keywords()

    except KeyboardInterrupt:
        log("\nStopped by user. Checkpoint saved - run again to resume.", "WARN")

    except (InvalidSessionIdException, WebDriverException) as error:
        log(f"Browser session ended unexpectedly: {error}", "ERROR")

    finally:
        try:
            driver.quit()
        except Exception:
            pass
        add_summary_sheet()
        dash.render()
        print("=" * 62)
        print(f"  Done  |  {dash.total} leads saved  |  {dash.high} HIGH priority")
        print(f"  File  : {config.OUTPUT_XLSX}")
        print("  Checkpoint + seen_urls saved for next run")
        print("=" * 62 + "\n")


if __name__ == "__main__":
    run()
