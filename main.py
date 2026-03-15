"""
NEXVIATECH - LinkedIn Founder Scraper v2.0
"""

import random
import sys

import config
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException

from core.browser import create_driver
from core.login import login
from core.scraper import scrape_profile
from core.search import search_profiles
from data.csv_writer import init_csv, save_lead
from utils.checkpoint import Checkpoint
from utils.human import delay_keywords, delay_profiles
from utils.logger import Dashboard, log
from utils.seen_urls import SeenUrls


def validate_config():
    if "your_email" in config.LINKEDIN_EMAIL:
        print("\nOpen config.py and set your LINKEDIN_EMAIL and LINKEDIN_PASSWORD.\n")
        sys.exit(1)


def print_banner():
    print("\n" + "=" * 62)
    print("  NEXVIATECH - LinkedIn Founder Scraper v2.0")
    print(f"  Keywords   : {', '.join(config.SEARCH_KEYWORDS)}")
    print(f"  Recency    : last {config.RECENCY_DAYS} days only")
    print(f"  Daily cap  : {config.DAILY_CAP} profiles")
    print(f"  Output     : {config.OUTPUT_CSV}")
    print(f"  Checkpoint : {config.CHECKPOINT_FILE}")
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


class ProxyPool:
    def __init__(self):
        self._pool = list(config.PROXIES)
        self._idx = 0

    def current(self):
        if not self._pool:
            return None
        return self._pool[self._idx % len(self._pool)]

    def rotate(self):
        if self._pool:
            self._idx += 1
            log(f"Proxy rotated -> {self.current()}", "INFO")


def run():
    validate_config()
    print_banner()

    checkpoint = Checkpoint()
    seen = SeenUrls()
    dash = Dashboard(print_every=5)
    proxies = ProxyPool()

    ask_resume(checkpoint)  # checkpoint.reset() is called inside if user chooses fresh start

    init_csv()
    driver = create_driver(proxy=proxies.current())

    try:
        if not login(driver):
            log("Login failed - aborting.", "ERROR")
            return

        for keyword in config.SEARCH_KEYWORDS:
            if dash.total >= config.DAILY_CAP:
                log(f"Daily cap ({config.DAILY_CAP}) reached. Stopping.", "WARN")
                break

            log(f"\n{'-' * 50}")
            log(f"Keyword: '{keyword}'")
            log(f"All-time seen URLs: {seen.count()}")
            log(f"{'-' * 50}")

            profile_urls = search_profiles(driver, keyword, seen)

            for url in profile_urls:
                if dash.total >= config.DAILY_CAP:
                    break

                if checkpoint.already_done(url):
                    log(f"  Checkpoint skip: ...{url[-30:]}", "SKIP")
                    dash.skip()
                    continue

                try:
                    lead = scrape_profile(driver, url, keyword)

                    if lead and lead.name:
                        save_lead(lead)
                        checkpoint.mark_done(url)
                        seen.add(url)
                        dash.record(lead.priority)
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

            log(f"\nKeyword '{keyword}' complete. Taking a break...")
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
        dash.render()

        print("=" * 62)
        print(f"  Done  |  {dash.total} leads saved  |  {dash.high} HIGH priority")
        print(f"  File  : {config.OUTPUT_CSV}")
        print("  Checkpoint + seen_urls saved for next run")
        print("=" * 62 + "\n")


if __name__ == "__main__":
    run()
