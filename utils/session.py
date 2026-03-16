# utils/session.py  -  Save and restore LinkedIn session cookies

import json
import os

import config
from utils.logger import log


def save_cookies(driver, path: str = config.COOKIES_FILE):
    """Save all current browser cookies to disk after successful login."""
    cookies = driver.get_cookies()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2)
    log(f"Session cookies saved ({len(cookies)} cookies).", "OK")


def load_cookies(driver, path: str = config.COOKIES_FILE) -> bool:
    """
    Load cookies from disk into the browser.
    Must be called after navigating to linkedin.com first.
    Returns True if cookies file existed and was loaded, False otherwise.
    """
    if not os.path.exists(path):
        return False

    with open(path, encoding="utf-8") as f:
        cookies = json.load(f)

    for cookie in cookies:
        cookie.pop("sameSite", None)
        cookie.pop("expiry", None)
        try:
            driver.add_cookie(cookie)
        except Exception:
            continue

    log(f"Session cookies loaded ({len(cookies)} cookies).", "OK")
    return True


def cookies_exist(path: str = config.COOKIES_FILE) -> bool:
    return os.path.exists(path)


def clear_cookies(path: str = config.COOKIES_FILE):
    """Delete saved cookies — forces fresh login next run."""
    if os.path.exists(path):
        os.remove(path)
        log("Saved cookies cleared.", "WARN")
