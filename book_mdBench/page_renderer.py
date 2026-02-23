"""
PDF page renderer — converts PDF pages to JPEG images.
"""

from pathlib import Path

from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError

from book_mdBench.config import IMAGE_DPI


class PageRenderer:
    """Render selected PDF pages to JPEG images."""

    def render(self, pdf_path: Path, indices: list[int], out_dir: Path) -> dict[int, Path]:
        """
        Render the given 0-based page *indices* from *pdf_path* to JPEG files in *out_dir*.

        Returns a dict mapping page index → Path of the saved image.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        rendered = {}

        try:
            # convert_from_path uses 1-based page numbers
            pages = convert_from_path(str(pdf_path), dpi=IMAGE_DPI)
        except PDFPageCountError as e:
            print(f"    ✗ PDF render failed: {e}")
            return rendered

        for idx in indices:
            if idx >= len(pages):
                continue
            img_path = out_dir / f"page_{idx:04d}.jpg"
            if not img_path.exists():
                pages[idx].save(str(img_path), "JPEG")
            rendered[idx] = img_path

        return rendered
