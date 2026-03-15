# utils/logger.py  -  Colored terminal logging + live dashboard

import logging
import os
from datetime import datetime

import config


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    BG_DARK = "\033[40m"


LEVEL_CONFIG = {
    "INFO": (C.CYAN, "i "),
    "OK": (C.GREEN, "+ "),
    "WARN": (C.YELLOW, "! "),
    "ERROR": (C.RED, "x "),
    "SCRAPE": (C.MAGENTA, "> "),
    "DATE": (C.BLUE, "- "),
    "SKIP": (C.GRAY, "-> "),
    "SCORE": (C.WHITE, "* "),
}

_file_logger = logging.getLogger("nexvia")
_file_logger.setLevel(logging.DEBUG)

try:
    os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True) if os.path.dirname(config.LOG_FILE) else None
    _fh = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _file_logger.addHandler(_fh)
except OSError:
    pass


def log(msg: str, level: str = "INFO"):
    color, icon = LEVEL_CONFIG.get(level, (C.WHITE, "  "))
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{C.GRAY}[{ts}]{C.RESET} {color}{icon}{msg}{C.RESET}")
    if _file_logger.handlers:
        _file_logger.info(f"[{level}] {msg}")


class Dashboard:
    """Tracks scraper stats and prints a live summary panel every N profiles."""

    def __init__(self, print_every: int = 5):
        self.total = 0
        self.high = 0
        self.medium = 0
        self.low = 0
        self.skipped = 0
        self.date_filtered = 0
        self.errors = 0
        self.print_every = print_every
        self.start_time = datetime.now()

    def record(self, priority: str):
        self.total += 1
        if priority == "HIGH":
            self.high += 1
        elif priority == "MEDIUM":
            self.medium += 1
        else:
            self.low += 1
        if self.total % self.print_every == 0:
            self.render()

    def skip(self):
        self.skipped += 1

    def date_filter(self):
        self.date_filtered += 1

    def error(self):
        self.errors += 1

    def elapsed(self) -> str:
        return str(datetime.now() - self.start_time).split(".")[0]

    def rate(self) -> float:
        secs = max((datetime.now() - self.start_time).total_seconds(), 1)
        return round(self.total / (secs / 60), 2)

    def render(self):
        width = 62
        sep = C.GRAY + "-" * width + C.RESET

        def bar(count, color, char="#"):
            return color + char * min(count, 20) + C.RESET

        print(f"\n{sep}")
        print(
            f"  {C.BOLD}{C.CYAN}NEXVIATECH SCRAPER{C.RESET}"
            f"  {C.GRAY}{datetime.now().strftime('%H:%M:%S')}{C.RESET}"
            f"  t {self.elapsed()}"
        )
        print(sep)
        print(
            f"  {C.GREEN}+ Saved      {C.RESET}: {C.BOLD}{self.total:<5}{C.RESET}"
            f"  {C.GREEN}HIGH   {self.high:<3}{C.RESET} {bar(self.high, C.GREEN)}"
        )
        print(
            f"  {C.BLUE}- Date skip  {C.RESET}: {self.date_filtered:<5}"
            f"  {C.YELLOW}MEDIUM {self.medium:<3}{C.RESET} {bar(self.medium, C.YELLOW, '=')}"
        )
        print(
            f"  {C.GRAY}-> Duplicates {C.RESET}: {self.skipped:<5}"
            f"  {C.GRAY}LOW    {self.low:<3}{C.RESET} {bar(self.low, C.GRAY, '.')}"
        )
        print(
            f"  {C.RED}x Errors     {C.RESET}: {self.errors:<5}"
            f"  rate {self.rate()} profiles/min"
        )
        print(f"{sep}\n")
