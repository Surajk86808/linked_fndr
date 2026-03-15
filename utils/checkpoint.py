# utils/checkpoint.py  -  Persist scrape progress, enable resume on crash

import json
import os
from datetime import datetime

import config


class Checkpoint:
    """Writes every scraped URL to disk immediately after processing."""

    def __init__(self, path: str = config.CHECKPOINT_FILE):
        self.path = path
        self._data = self._load()

    def already_done(self, url: str) -> bool:
        return url in self._url_set

    def mark_done(self, url: str):
        if url not in self._url_set:
            self._data["scraped_urls"].append(url)
            self._data["total_scraped"] += 1
            self._url_set.add(url)
        self._save()

    def total(self) -> int:
        return self._data.get("total_scraped", 0)

    def reset(self):
        if os.path.exists(self.path):
            os.remove(self.path)
        self._data = self._empty()
        self._url_set = set()
        self._save()

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def _load(self) -> dict:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as file:
                data = json.load(file)
            self._url_set = set(data.get("scraped_urls", []))
            return data
        self._url_set = set()
        return self._empty()

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(self._data, file, indent=2)

    @staticmethod
    def _empty() -> dict:
        return {
            "session_start": str(datetime.now()),
            "total_scraped": 0,
            "scraped_urls": [],
        }
