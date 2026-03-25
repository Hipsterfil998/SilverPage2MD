"""
Markdown page splitting and stratified sampling.

Split strategy per section:
  1. [p. N] markers  — original book pagination (if present)
  2. ~2800-char blocks — paragraph-boundary fallback
"""

import random
import re
from config import MIN_MD_CHARS, N_FRONT_MANDATORY, STRATA

_PAGE_MARKER = re.compile(r"(?=\[p\. \d+\])")
_PAGE_CHARS  = 2800   # approx. chars per A4 page at 11pt / 2.5cm margins


class PageSampler:
    """Split EPUB sections into page-sized chunks and sample stratified by zone."""

    def split(self, sections: list[dict]) -> list[dict]:
        """
        Return a flat list of page-sized chunks.

        Each section is split at [p. N] markers when present;
        otherwise divided into ~_PAGE_CHARS-char blocks at paragraph boundaries.
        Chunks shorter than MIN_MD_CHARS are discarded.
        """
        chunks = []
        for section in sections:
            md = section.get("md", "").strip()
            if len(md) < MIN_MD_CHARS:
                continue
            for piece in self._split_section(md, section["id"]):
                chunks.append(piece)
        return chunks

    def sample(self, n_chunks: int) -> dict[str, list[int]]:
        """
        Sample chunk indices stratified across front / body / back zones.
        The first N_FRONT_MANDATORY chunks are always included.

        Returns a dict mapping zone name → list of sampled indices.
        """
        mandatory = list(range(min(N_FRONT_MANDATORY, n_chunks)))

        start      = len(mandatory)
        front_size = max(STRATA["front"] + 1, (n_chunks - start) // 10)
        front_end  = start + min(front_size, (n_chunks - start) // 3)
        back_start = n_chunks - min(front_size, (n_chunks - start) // 3)

        zones = {
            "front": list(range(start, front_end)),
            "body":  list(range(front_end, back_start)),
            "back":  list(range(back_start, n_chunks)),
        }

        sampled = {"mandatory": mandatory}
        for zone, k in STRATA.items():
            pool = zones[zone]
            sampled[zone] = random.sample(pool, min(k, len(pool)))

        return sampled

    # ── internals ─────────────────────────────────────────────────────────────

    def _split_section(self, md: str, section_id: str) -> list[dict]:
        """Split by page markers if present, otherwise by character count."""
        parts = _PAGE_MARKER.split(md)
        chunks = [
            {"id": section_id, "md": p.strip() + "\n"}
            for p in parts
            if len(p.strip()) >= MIN_MD_CHARS
        ]
        if len(chunks) >= 2:
            return chunks
        return self._by_char_count(md, section_id)

    @staticmethod
    def _by_char_count(md: str, section_id: str) -> list[dict]:
        """Split into ~_PAGE_CHARS-char blocks at paragraph boundaries."""
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", md) if p.strip()]
        pages: list[dict] = []
        current: list[str] = []
        current_len = 0

        for para in paragraphs:
            current.append(para)
            current_len += len(para)
            if current_len >= _PAGE_CHARS:
                pages.append({"id": section_id, "md": "\n\n".join(current) + "\n"})
                current, current_len = [], 0

        if current:
            tail = "\n\n".join(current) + "\n"
            if len(tail.strip()) >= MIN_MD_CHARS:
                pages.append({"id": section_id, "md": tail})

        return pages
