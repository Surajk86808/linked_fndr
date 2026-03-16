# core/login.py  -  LinkedIn login with cookie session + credential fallback

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import config
from utils.human import delay_after_login, human_type, short_pause
from utils.logger import log
from utils.session import cookies_exist, load_cookies, save_cookies

LOGIN_URL = "https://www.linkedin.com/login?trk=guest_homepage-basic_nav-header-signin"


def login(driver: webdriver.Chrome) -> bool:
    """
    Try cookie login first. Falls back to credential login if cookies
    are missing or expired. Saves fresh cookies after every credential login.
    """
    log("Navigating to LinkedIn...")
    driver.get("https://www.linkedin.com")
    delay_after_login()

    # --- Step 1: Try cookie login ---
    if cookies_exist():
        log("Found saved session — attempting cookie login...", "INFO")
        load_cookies(driver)
        driver.get("https://www.linkedin.com/feed")
        delay_after_login()

        if _is_logged_in(driver):
            log("Cookie login successful — skipping credentials.", "OK")
            return True
        else:
            log("Cookies expired or invalid — falling back to credential login.", "WARN")

    # --- Step 2: Credential login ---
    log("Logging in with credentials...")
    driver.get(LOGIN_URL)
    delay_after_login()

    if _is_logged_in(driver):
        log("Already logged in.", "OK")
        save_cookies(driver)
        return True

    wait = WebDriverWait(driver, 20)

    try:
        email_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        short_pause()
        human_type(email_field, config.LINKEDIN_EMAIL)
        short_pause()

        pass_field = driver.find_element(By.ID, "password")
        human_type(pass_field, config.LINKEDIN_PASSWORD)
        short_pause()
        pass_field.send_keys(Keys.RETURN)

        log("Credentials submitted. Waiting for redirect...")
        delay_after_login()

        current = driver.current_url
        if any(x in current for x in ["checkpoint", "challenge", "captcha", "verify"]):
            log("LinkedIn is asking for verification!", "WARN")
            log("Complete the check in the browser window.", "WARN")
            log("Then press ENTER here to continue...", "WARN")
            input()
            delay_after_login()

        WebDriverWait(driver, 25).until(
            lambda d: any(x in d.current_url for x in ["feed", "mynetwork", "jobs", "in/"])
        )

        log("Login successful!", "OK")
        save_cookies(driver)
        return True

    except TimeoutException:
        log("Login timed out.", "ERROR")
        input("Press ENTER to try continuing anyway, or Ctrl+C to abort...")
        if _is_logged_in(driver):
            save_cookies(driver)
            return True
        return False


def _is_logged_in(driver: webdriver.Chrome) -> bool:
    try:
        driver.find_element(By.CSS_SELECTOR, "div.feed-identity-module")
        return True
    except Exception:
        pass
    return "feed" in driver.current_url or "mynetwork" in driver.current_url
