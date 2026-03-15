# core/login.py  -  LinkedIn login with CAPTCHA / verification handling

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import config
from utils.human import delay_after_login, human_type, short_pause
from utils.logger import log

LOGIN_URL = "https://www.linkedin.com/login?trk=guest_homepage-basic_nav-header-signin"


def login(driver: webdriver.Chrome) -> bool:
    """
    Log into LinkedIn.

    Returns True on success, False on failure.
    Handles:
      - Normal login flow
      - Email verification / CAPTCHA - pauses and lets user solve manually
      - Already-logged-in sessions (skips re-login)
    """
    log("Navigating to LinkedIn login page...")
    driver.get(LOGIN_URL)
    delay_after_login()

    if _is_logged_in(driver):
        log("Already logged in - skipping login step.", "OK")
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
        return True

    except TimeoutException:
        log("Login timed out. Browser may be stuck.", "ERROR")
        log("Press ENTER to try continuing anyway, or Ctrl+C to abort...")
        input()
        return _is_logged_in(driver)


def _is_logged_in(driver: webdriver.Chrome) -> bool:
    """Check if the session already has a valid LinkedIn login."""
    try:
        driver.find_element(By.CSS_SELECTOR, "div.feed-identity-module")
        return True
    except Exception:
        pass
    return "feed" in driver.current_url or "mynetwork" in driver.current_url
