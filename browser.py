# core/browser.py  —  Chrome driver creation with stealth configuration

import random

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

from logger import log


_RESOLUTIONS = [
    (1440, 900),
    (1536, 864),
    (1366, 768),
    (1920, 1080),
    (1280, 800),
    (1600, 900),
]


def create_driver(proxy: str = None) -> webdriver.Chrome:
    """
    Build a Chrome WebDriver with a stable Windows fingerprint.
    Avoid overriding the user-agent with stale cross-platform values.
    """
    options = Options()
    width, height = random.choice(_RESOLUTIONS)

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    options.add_argument(f"--window-size={width},{height}")
    options.add_argument("--start-maximized")
    options.add_argument("--lang=en-US,en;q=0.9")

    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")

    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)

    if proxy:
        options.add_argument(f"--proxy-server={proxy}")
        log(f"Proxy active: {proxy}", "INFO")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        { name: 'Chrome PDF Plugin' },
                        { name: 'Chrome PDF Viewer' },
                        { name: 'Native Client' },
                    ]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                window.chrome = {
                    runtime: {},
                    loadTimes: function(){},
                    csi: function(){},
                    app: {}
                };
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications'
                        ? Promise.resolve({ state: Notification.permission })
                        : originalQuery(parameters)
                );
            """
        },
    )

    browser_version = driver.capabilities.get("browserVersion", "unknown")
    actual_ua = driver.execute_script("return navigator.userAgent")
    log(f"Browser ready — Chrome {browser_version}", "OK")
    log(f"Browser UA — {actual_ua}", "INFO")
    return driver
