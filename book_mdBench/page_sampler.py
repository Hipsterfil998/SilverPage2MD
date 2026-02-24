"""
Markdown page splitting and stratified sampling.
"""

import random
from book_mdBench.config import MIN_MD_CHARS, N_FRONT_MANDATORY, STRATA


class PageSampler:
    """Filter EPUB sections and sample page indices stratified by zone."""

    def split(self, sections: list[dict]) -> list[dict]:
        """
        Filter out near-empty sections (less than MIN_MD_CHARS in their markdown).
        The input is the list of dicts produced by EpubConverter.get_sections().
        """
        return [s for s in sections if len(s.get("md", "").strip()) >= MIN_MD_CHARS]

    def sample(self, n_chunks: int) -> dict[str, list[int]]:
        """
        Sample section indices stratified across front / body / back zones.
        The first N_FRONT_MANDATORY sections are always included.

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
