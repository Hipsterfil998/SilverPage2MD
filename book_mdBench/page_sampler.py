"""
Markdown page splitting and stratified sampling.
"""

import random
import re
from pathlib import Path

from book_mdBench.config import MIN_MD_CHARS, STRATA


class PageSampler:
    """Split a markdown file into chunks and sample pages stratified by zone."""

    def split(self, md_path: Path) -> list[str]:
        """Split markdown into chunks on level-1/2 headings. Returns list of chunks."""
        text = md_path.read_text(encoding="utf-8")
        parts = re.split(r"(?=^#{1,2} )", text, flags=re.MULTILINE)
        return [p for p in parts if len(p.strip()) >= MIN_MD_CHARS]

    def sample(self, n_chunks: int) -> dict[str, list[int]]:
        """
        Sample page indices stratified across front / body / back zones.

        Returns a dict mapping zone name → list of sampled indices.
        """
        front_end = max(1, n_chunks // 5)
        back_start = n_chunks - max(1, n_chunks // 5)

        zones = {
            "front": list(range(0, front_end)),
            "body":  list(range(front_end, back_start)),
            "back":  list(range(back_start, n_chunks)),
        }

        sampled = {}
        for zone, k in STRATA.items():
            pool = zones[zone]
            sampled[zone] = random.sample(pool, min(k, len(pool)))

        return sampled
