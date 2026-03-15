# utils/seen_urls.py  —  Permanent all-time URL deduplication
#
# checkpoint.json resets between runs.
# seen_urls.txt NEVER resets — a profile scraped 3 months ago
# will never be scraped again as long as this file exists.

import os
from pathlib import Path
from config import SEEN_URLS_FILE


class SeenUrls:
    """
    Append-only flat-file store of every LinkedIn URL ever visited.
    Loaded into a set at startup for O(1) lookups.
    """

    def __init__(self, path: str = SEEN_URLS_FILE):
        self.path = path
        self._urls = self._load()

    def seen(self, url: str) -> bool:
        return url in self._urls

    def add(self, url: str):
        """Add URL to in-memory set and append to file immediately."""
        if url not in self._urls:
            self._urls.add(url)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(url + "\n")

    def count(self) -> int:
        return len(self._urls)

    def _load(self) -> set:
        if not os.path.exists(self.path):
            return set()
        return set(Path(self.path).read_text(encoding="utf-8").splitlines())
