"""
Client for the Gutendex API (Project Gutenberg).
"""

import random
from pathlib import Path

import requests

from book_mdBench.config import GUTENDEX_URL


class GutenbergClient:
    """Search and download books from Project Gutenberg via Gutendex."""

    def sample(self, lang_code: str, n: int) -> list[dict]:
        """Return up to *n* books with EPUB downloads for the given language."""
        books, page = [], 1
        while len(books) < n:
            resp = requests.get(
                GUTENDEX_URL,
                params={"languages": lang_code, "page": page},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            for book in data.get("results", []):
                epub_url = self._epub_url(book)
                if epub_url:
                    books.append({
                        "id":       book["id"],
                        "title":    book["title"],
                        "authors":  [a["name"] for a in book.get("authors", [])],
                        "epub_url": epub_url,
                    })
                    if len(books) >= n:
                        break
            if not data.get("next"):
                break
            page += 1

        random.shuffle(books)
        return books[:n]

    def download_epub(self, url: str, dest: Path) -> bool:
        """Download an EPUB file. Returns True on success."""
        if dest.exists():
            return True
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            return True
        except Exception as e:
            print(f"    ✗ Download failed: {e}")
            return False

    @staticmethod
    def _epub_url(book: dict) -> str | None:
        """Extract the EPUB download URL from a Gutendex book record."""
        formats = book.get("formats", {})
        for mime in ("application/epub+zip", "application/epub"):
            if mime in formats:
                return formats[mime]
        return None
