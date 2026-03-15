# utils/human.py  -  Human-like timing, typing, scrolling, mouse movement

import random
import time

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

import config


def pause(min_s: float, max_s: float):
    """Sleep for a random duration between min_s and max_s."""
    time.sleep(random.uniform(min_s, max_s))


def delay_profiles():
    pause(*config.DELAY_BETWEEN_PROFILES)


def delay_keywords():
    pause(*config.DELAY_BETWEEN_KEYWORDS)


def delay_pages():
    pause(*config.DELAY_BETWEEN_PAGES)


def delay_page_load():
    pause(*config.DELAY_PAGE_LOAD)


def delay_contact_modal():
    pause(*config.DELAY_CONTACT_MODAL)


def delay_after_login():
    pause(*config.DELAY_AFTER_LOGIN)


def short_pause():
    pause(0.3, 0.9)


def micro_pause():
    pause(config.TYPING_SPEED_MIN, config.TYPING_SPEED_MAX)


def human_type(element: WebElement, text: str):
    """Type text into a field one character at a time with random delays."""
    for index, char in enumerate(text):
        element.send_keys(char)
        micro_pause()
        if index > 0 and index % random.randint(5, 10) == 0:
            pause(0.15, 0.55)


def human_scroll(driver: webdriver.Chrome, steps: int = None, px_base: int = None):
    """Scroll the page in natural increments with slight jitter and random pauses."""
    steps = steps or config.SCROLL_STEPS
    px_base = px_base or config.SCROLL_PX_BASE
    jitter = config.SCROLL_PX_JITTER

    for _ in range(steps):
        px = px_base + random.randint(-jitter, jitter)
        driver.execute_script(f"window.scrollBy(0, {px})")
        pause(0.3, 1.0)

    if random.random() < 0.25:
        driver.execute_script(f"window.scrollBy(0, -{random.randint(100, 300)})")
        pause(0.4, 0.9)


def scroll_to_bottom(driver: webdriver.Chrome):
    total_height = driver.execute_script("return document.body.scrollHeight")
    current = 0
    step = random.randint(300, 500)
    while current < total_height:
        current = min(current + step, total_height)
        driver.execute_script(f"window.scrollTo(0, {current})")
        pause(0.25, 0.7)
        step = random.randint(250, 550)


def wiggle_mouse(driver: webdriver.Chrome):
    width = driver.execute_script("return window.innerWidth")
    height = driver.execute_script("return window.innerHeight")

    for _ in range(random.randint(3, 7)):
        x = random.randint(100, width - 100)
        y = random.randint(100, height - 100)
        driver.execute_script(
            f"document.dispatchEvent(new MouseEvent('mousemove', "
            f"{{clientX: {x}, clientY: {y}, bubbles: true}}));"
        )
        pause(0.08, 0.25)


def safe_click(driver: webdriver.Chrome, element: WebElement):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    pause(0.3, 0.8)
    wiggle_mouse(driver)
    pause(0.2, 0.5)
    element.click()
