"""
Benchmark dataset builder.

Orchestrates the full pipeline:
  1. Search and download EPUBs from Project Gutenberg
  2. Convert EPUB → markdown (ground truth) and PDF (model input)
  3. Sample pages stratified across front/body/back
  4. Render sampled PDF pages to JPEG images
  5. Save aligned (image, markdown) pairs with metadata
"""

import json
from pathlib import Path
from config import LANGUAGES, N_BOOKS, OUTPUT_DIR
from gutenberg_client import GutenbergClient
from epub_converter import EpubConverter
from page_sampler import PageSampler
from page_renderer import PageRenderer


class BenchmarkBuilder:
    """Orchestrates the full benchmark dataset construction pipeline."""

    def __init__(self):
        self.client   = GutenbergClient()
        self.converter = EpubConverter()
        self.sampler  = PageSampler()
        self.renderer = PageRenderer()

    def process_book(self, book: dict, lang_dir: Path) -> dict | None:
        """Run the full pipeline for a single book."""
        book_dir  = lang_dir / str(book["id"])
        pages_dir = book_dir / "pages"
        book_dir.mkdir(parents=True, exist_ok=True)

        print(f"  → [{book['id']}] {book['title']}")

        epub_path = book_dir / "book.epub"
        md_path   = book_dir / "book.md"
        pdf_path  = book_dir / "book.pdf"

        # download and convert
        if not self.client.download_epub(book["epub_url"], epub_path):
            return None
        if not self.converter.to_markdown(epub_path, md_path):
            return None
        if not self.converter.to_pdf(epub_path, pdf_path):
            return None

        # split and sample
        chunks = self.sampler.split(md_path)
        if len(chunks) < 10:
            print(f"    ✗ Too few chunks ({len(chunks)}), skipping")
            return None

        sampled     = self.sampler.sample(len(chunks))
        all_indices = sorted(i for indices in sampled.values() for i in indices)

        # render pages
        rendered = self.renderer.render(pdf_path, all_indices, pages_dir)

        # save aligned (image, markdown) pairs
        page_records = []
        for zone, indices in sampled.items():
            for idx in indices:
                if idx not in rendered:
                    continue
                chunk_path = pages_dir / f"page_{idx:04d}.md"
                chunk_path.write_text(chunks[idx], encoding="utf-8")
                page_records.append({
                    "page_idx": idx,
                    "zone":     zone,
                    "img_path": str(rendered[idx]),
                    "md_path":  str(chunk_path),
                })

        print(f"    ✓ {len(page_records)} pages saved")
        return {
            "id":      book["id"],
            "title":   book["title"],
            "authors": book["authors"],
            "pages":   page_records,
        }

    def build(self):
        """Run the full pipeline for all languages."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        all_metadata = {}

        for language, lang_code in LANGUAGES.items():
            print(f"\n{'='*50}\nLanguage: {language}\n{'='*50}")

            lang_dir = OUTPUT_DIR / language
            lang_dir.mkdir(exist_ok=True)

            books   = self.client.sample(lang_code, N_BOOKS)
            results = []

            for book in books:
                result = self.process_book(book, lang_dir)
                if result:
                    results.append(result)

            all_metadata[language] = results
            (lang_dir / "metadata.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"\n✓ {len(results)}/{N_BOOKS} books completed for {language}")

        (OUTPUT_DIR / "metadata.json").write_text(
            json.dumps(all_metadata, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"\n✓ Done. Dataset saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    BenchmarkBuilder().build()