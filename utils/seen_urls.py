# utils/seen_urls.py  -  Permanent all-time URL deduplication

import os
from pathlib import Path

import config


class SeenUrls:
    """Append-only flat-file store of every LinkedIn URL ever visited."""

    def __init__(self, path: str = config.SEEN_URLS_FILE):
        self.path = path
        self._urls = self._load()

    def seen(self, url: str) -> bool:
        return url in self._urls

    def add(self, url: str):
        if url not in self._urls:
            self._urls.add(url)
            with open(self.path, "a", encoding="utf-8") as file:
                file.write(url + "\n")

    def count(self) -> int:
        return len(self._urls)

    def _load(self) -> set:
        if not os.path.exists(self.path):
            return set()
        return set(Path(self.path).read_text(encoding="utf-8").splitlines())
