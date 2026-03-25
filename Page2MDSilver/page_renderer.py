"""
Chunk renderer — converts Markdown chunks to JPEG images.

Pipeline: Markdown ──pandoc (xelatex)──► PDF ──► JPEG (page 1)

Since both the JPEG and the ground-truth Markdown come from the same source,
they are guaranteed to represent exactly the same content.

System requirements:
    sudo apt-get install -y pandoc texlive-xetex \
        texlive-lang-italian texlive-lang-german poppler-utils
"""

import re
import subprocess
import tempfile
from pathlib import Path

from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError

from config import IMAGE_DPI, IMAGE_QUALITY


class PageRenderer:
    """Render Markdown chunks to JPEG images via LaTeX."""

    def render(
        self,
        sections: list[dict],
        indices: list[int],
        out_dir: Path,
        lang: str = "it",
    ) -> dict[int, Path]:
        """
        For each index in *indices*, render sections[index]['md'] to a JPEG.

        *lang* is a BCP 47 language code (e.g. 'it', 'de') used by LaTeX
        for hyphenation and typography.

        Returns a dict mapping section index → Path of the saved JPEG.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        rendered = {}

        for idx in indices:
            img_path = out_dir / f"page_{idx:04d}.jpg"
            if img_path.exists():
                rendered[idx] = img_path
                continue

            image = self._md_to_image(sections[idx]["md"], lang=lang)
            if image is None:
                continue

            image.save(str(img_path), "JPEG", quality=IMAGE_QUALITY)
            rendered[idx] = img_path

        return rendered

    # ── internals ─────────────────────────────────────────────────────────────

    # Image references in the ground-truth MD (e.g. ![image_1](images/image_1.png))
    # are stripped before rendering because the files don't exist on disk.
    _IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")

    def _md_to_image(self, text: str, lang: str = "it"):
        """Convert a Markdown string to a PIL image (first PDF page) via xelatex."""
        with tempfile.TemporaryDirectory() as tmp:
            md_path  = Path(tmp) / "chunk.md"
            pdf_path = Path(tmp) / "chunk.pdf"

            # Strip image references — files aren't on disk, xelatex would fail
            render_text = self._IMG_RE.sub("", text)
            md_path.write_text(render_text, encoding="utf-8")

            result = subprocess.run(
                [
                    "pandoc", str(md_path),
                    "-o", str(pdf_path),
                    "--pdf-engine=xelatex",
                    f"-V", f"lang={lang}",
                    "-V", "papersize=a4",
                    "-V", "geometry:margin=2.5cm",
                    "-V", "fontsize=11pt",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                print(f"      ✗ MD→PDF failed: {result.stderr[:200]}")
                return None

            try:
                pages = convert_from_path(str(pdf_path), dpi=IMAGE_DPI)
                return pages[0] if pages else None
            except PDFPageCountError as e:
                print(f"      ✗ PDF→IMG failed: {e}")
                return None
