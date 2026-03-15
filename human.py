# utils/human.py  —  Human-like timing, typing, scrolling, mouse movement
#
# Every interaction with the browser goes through this module.
# Centralising it here means you can tune all timing from config.py
# without touching any scraping logic.

import random
import time

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

import config


# ══════════════════════════════════════════════════════════════════
#  Core delay
# ══════════════════════════════════════════════════════════════════

def pause(min_s: float, max_s: float):
    """Sleep for a random duration between min_s and max_s."""
    time.sleep(random.uniform(min_s, max_s))


def delay_profiles():
    """Delay between visiting two profiles."""
    pause(*config.DELAY_BETWEEN_PROFILES)


def delay_keywords():
    """Longer break between keyword search batches."""
    pause(*config.DELAY_BETWEEN_KEYWORDS)


def delay_pages():
    """Delay between search result pages."""
    pause(*config.DELAY_BETWEEN_PAGES)


def delay_page_load():
    """Wait after any page navigation."""
    pause(*config.DELAY_PAGE_LOAD)


def delay_contact_modal():
    """Wait after opening the contact-info modal."""
    pause(*config.DELAY_CONTACT_MODAL)


def delay_after_login():
    """Wait after successful login before any action."""
    pause(*config.DELAY_AFTER_LOGIN)


def short_pause():
    """Very short think-time pause (0.3 – 0.9 s)."""
    pause(0.3, 0.9)


def micro_pause():
    """Between-character typing pause."""
    pause(config.TYPING_SPEED_MIN, config.TYPING_SPEED_MAX)


# ══════════════════════════════════════════════════════════════════
#  Typing
# ══════════════════════════════════════════════════════════════════

def human_type(element: WebElement, text: str):
    """
    Type text into a field one character at a time with random
    per-keystroke delays. Occasionally adds a small 'think pause'
    mid-word to simulate a real person.
    """
    for i, char in enumerate(text):
        element.send_keys(char)
        micro_pause()
        # Random longer pause every 5–10 chars (like thinking)
        if i > 0 and i % random.randint(5, 10) == 0:
            pause(0.15, 0.55)


# ══════════════════════════════════════════════════════════════════
#  Scrolling
# ══════════════════════════════════════════════════════════════════

def human_scroll(driver: webdriver.Chrome,
                 steps: int = None,
                 px_base: int = None):
    """
    Scroll the page in natural increments with slight jitter and
    random pauses between each step.
    """
    steps   = steps   or config.SCROLL_STEPS
    px_base = px_base or config.SCROLL_PX_BASE
    jitter  = config.SCROLL_PX_JITTER

    for _ in range(steps):
        px = px_base + random.randint(-jitter, jitter)
        driver.execute_script(f"window.scrollBy(0, {px})")
        pause(0.3, 1.0)

    # Occasionally scroll back up a little (humans do this)
    if random.random() < 0.25:
        driver.execute_script(f"window.scrollBy(0, -{random.randint(100, 300)})")
        pause(0.4, 0.9)


def scroll_to_bottom(driver: webdriver.Chrome):
    """Scroll all the way to the bottom of the page gradually."""
    total_height = driver.execute_script("return document.body.scrollHeight")
    current      = 0
    step         = random.randint(300, 500)
    while current < total_height:
        current = min(current + step, total_height)
        driver.execute_script(f"window.scrollTo(0, {current})")
        pause(0.25, 0.7)
        step = random.randint(250, 550)


# ══════════════════════════════════════════════════════════════════
#  Mouse simulation (via JS)
# ══════════════════════════════════════════════════════════════════

def wiggle_mouse(driver: webdriver.Chrome):
    """
    Dispatch synthetic mousemove events to random positions.
    Helps defeat basic bot-detection that monitors mouse inactivity.
    """
    w = driver.execute_script("return window.innerWidth")
    h = driver.execute_script("return window.innerHeight")

    for _ in range(random.randint(3, 7)):
        x = random.randint(100, w - 100)
        y = random.randint(100, h - 100)
        driver.execute_script(
            f"document.dispatchEvent(new MouseEvent('mousemove', "
            f"{{clientX: {x}, clientY: {y}, bubbles: true}}));"
        )
        pause(0.08, 0.25)


# ══════════════════════════════════════════════════════════════════
#  Safe click
# ══════════════════════════════════════════════════════════════════

def safe_click(driver: webdriver.Chrome, element: WebElement):
    """
    Scroll element into view, wiggle mouse nearby, then click.
    More human than a direct .click() call.
    """
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    pause(0.3, 0.8)
    wiggle_mouse(driver)
    pause(0.2, 0.5)
    element.click()
