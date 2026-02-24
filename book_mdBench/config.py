"""
Benchmark dataset configuration.
"""

from pathlib import Path


# ── dataset parameters ────────────────────────────────────────────────────────

LANGUAGES: dict[str, str] = {
    "italian": "it",
    "german":  "de",
}

N_BOOKS           = 15
N_PAGES           = 20
N_FRONT_MANDATORY = 3   # first N chunks always included (frontmatter)
STRATA            = {"front": 2, "body": 10, "back": 5}  # sampled after mandatory
MIN_MD_CHARS = 150   # min chars in a markdown chunk to be considered non-blank
IMAGE_DPI     = 200  # DPI for page image rendering
IMAGE_QUALITY = 92   # JPEG quality (0-95)
OUTPUT_DIR   = Path("./benchmark_data")


# ── external URLs ─────────────────────────────────────────────────────────────

GUTENDEX_URL = "https://gutendex.com/books/"