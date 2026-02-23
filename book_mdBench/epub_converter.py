"""
EPUB conversion utilities.
"""

import subprocess
from pathlib import Path

import pypandoc


class EpubConverter:
    """Convert EPUB files to Markdown and PDF."""

    def to_markdown(self, epub_path: Path, md_path: Path) -> bool:
        """Convert EPUB → Markdown via pandoc. Returns True on success."""
        if md_path.exists():
            return True
        try:
            pypandoc.convert_file(
                str(epub_path),
                "markdown",
                outputfile=str(md_path),
                extra_args=["--wrap=none"],
            )
            return True
        except Exception as e:
            print(f"    ✗ EPUB→MD failed: {e}")
            return False

    def to_pdf(self, epub_path: Path, pdf_path: Path) -> bool:
        """Convert EPUB → PDF via pandoc + wkhtmltopdf. Returns True on success."""
        if pdf_path.exists():
            return True
        try:
            result = subprocess.run(
                ["pandoc", str(epub_path), "-o", str(pdf_path), "--pdf-engine=wkhtmltopdf"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                print(f"    ✗ EPUB→PDF failed: {result.stderr[:200]}")
                return False
            return True
        except Exception as e:
            print(f"    ✗ EPUB→PDF failed: {e}")
            return False
