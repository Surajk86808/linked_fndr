# utils/checkpoint.py  —  Persist scrape progress, enable resume on crash

import json
import os
from datetime import datetime
from config import CHECKPOINT_FILE


class Checkpoint:
    """
    Writes every scraped URL to disk immediately after processing.

    On crash or Ctrl+C, run the scraper again and choose Resume —
    all previously-processed URLs are skipped automatically.

    File format (checkpoint.json):
    {
        "session_start": "2025-01-15 09:00:00",
        "total_scraped": 34,
        "scraped_urls": ["https://linkedin.com/in/abc", ...]
    }
    """

    def __init__(self, path: str = CHECKPOINT_FILE):
        self.path = path
        self._data = self._load()

    # ── Public API ────────────────────────────────────────────────

    def already_done(self, url: str) -> bool:
        """Return True if this URL was processed in a previous run."""
        return url in self._url_set

    def mark_done(self, url: str):
        """Record a URL as processed and flush to disk immediately."""
        if url not in self._url_set:
            self._data["scraped_urls"].append(url)
            self._data["total_scraped"] += 1
            self._url_set.add(url)
        self._save()

    def total(self) -> int:
        return self._data.get("total_scraped", 0)

    def reset(self):
        """Start fresh — deletes existing checkpoint file."""
        if os.path.exists(self.path):
            os.remove(self.path)
        self._data    = self._empty()
        self._url_set = set()
        self._save()

    def exists(self) -> bool:
        return os.path.exists(self.path)

    # ── Private ───────────────────────────────────────────────────

    def _load(self) -> dict:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self._url_set = set(data.get("scraped_urls", []))
            return data
        self._url_set = set()
        return self._empty()

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    @staticmethod
    def _empty() -> dict:
        return {
            "session_start": str(datetime.now()),
            "total_scraped": 0,
            "scraped_urls":  [],
        }
