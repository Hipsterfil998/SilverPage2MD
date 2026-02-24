"""
EPUB conversion utilities.

Parses an EPUB (ZIP) to extract HTML sections in spine order and converts
each section to clean Markdown for use as ground-truth labels.
"""

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath

import pypandoc


class EpubConverter:
    """Parse EPUB files: extract ordered HTML sections and convert to Markdown."""

    _OPF_NS  = "http://www.idpf.org/2007/opf"
    _CONT_NS = "urn:oasis:names:tc:opendocument:xmlns:container"

    # ── public API ────────────────────────────────────────────────────────────

    def get_sections(self, epub_path: Path) -> list[dict]:
        """
        Return ordered sections from the EPUB spine.

        Each section is a dict with keys:
          'id' – item id from the OPF manifest
          'md' – clean Markdown converted from the section HTML
        """
        sections = []
        for sid, html in self._parse_spine(epub_path):
            md = self._html_to_markdown(html)
            if len(md.strip()) >= 50:
                sections.append({"id": sid, "md": md})
        return sections

    # ── EPUB spine parsing ────────────────────────────────────────────────────

    def _parse_spine(self, epub_path: Path) -> list[tuple[str, str]]:
        """Return [(section_id, html_content), ...] in spine order."""
        with zipfile.ZipFile(epub_path) as zf:
            container = ET.fromstring(zf.read("META-INF/container.xml"))
            opf_path  = container.find(
                f".//{{{self._CONT_NS}}}rootfile"
            ).get("full-path")
            opf_dir = str(PurePosixPath(opf_path).parent)

            opf = ET.fromstring(zf.read(opf_path))

            manifest = {
                item.get("id"): item.get("href")
                for item in opf.findall(f".//{{{self._OPF_NS}}}item")
            }

            sections = []
            for itemref in opf.findall(f".//{{{self._OPF_NS}}}itemref"):
                idref = itemref.get("idref")
                href  = manifest.get(idref, "")
                if not href.lower().endswith((".html", ".xhtml", ".htm")):
                    continue
                full = href if opf_dir == "." else str(PurePosixPath(opf_dir) / href)
                try:
                    html = zf.read(full).decode("utf-8", errors="replace")
                    sections.append((idref, html))
                except KeyError:
                    pass

        return sections

    # ── HTML → Markdown ───────────────────────────────────────────────────────

    def _html_to_markdown(self, html: str) -> str:
        """Convert an HTML string to clean Markdown via pandoc.

        Output format extensions used:
          tex_math_dollars – inline math as $...$ and block math as $$...$$
          pipe_tables      – HTML tables → Markdown pipe tables
        Lists, indentation and heading hierarchy are preserved by default.
        """
        try:
            md = pypandoc.convert_text(
                html,
                "markdown+tex_math_dollars+pipe_tables",
                format="html",
                extra_args=["--wrap=none"],
            )
        except Exception:
            return ""
        return self._clean(md)

    # ── cleaning ──────────────────────────────────────────────────────────────

    def _clean(self, text: str) -> str:
        """
        Post-process pandoc Markdown output.

        Removes:
          - YAML front matter, pandoc fenced divs, inline CSS attribute spans
          - Empty anchor spans []{#id} (EPUB page anchors as noise)
          - Excessive blank lines

        Preserves / normalises:
          - Heading hierarchy: # ## ### (unchanged)
          - Tables → Markdown pipe tables (via pandoc extension)
          - Math → $...$ inline, $$...$$ block (via pandoc extension)
          - Lists and indentation (unchanged)
          - Images → ![image_N](images/image_N.png) numbered sequentially
          - Page number markers → [p. N]
          - Footnotes [^N] and their definitions
        """

        # 1. YAML front matter
        text = re.sub(r"^---\n.*?\n---\n?", "", text, flags=re.DOTALL)

        # 2. Pandoc fenced divs  (::: {#id .class} … :::)
        text = re.sub(r"^:{3,}[^\n]*$", "", text, flags=re.MULTILINE)

        # 3. Heading links with attribute blocks
        #    ### [TITLE](#ref){.toc-backref} {.center}  →  ### TITLE
        text = re.sub(
            r"^(#{1,6}[ \t]+)\[([^\]]+)\]\([^)]*\)([ \t]*\{[^}]*\})*",
            r"\1\2",
            text,
            flags=re.MULTILINE,
        )

        # 4. Inline attribute spans  {.class #id key="val"}
        text = re.sub(r"\{[^}\n]{0,200}\}", "", text)

        # 5. Empty anchor spans from EPUB page anchors:  []{#page5}  →  remove
        text = re.sub(r"\[\]\{[^}]*\}", "", text)

        # 6. Page number markers  \[pg!5\]  \[pg 5\]  \[Pg.5\]  →  [p. 5]
        text = re.sub(
            r"\\\[[Pp]g[!.\s]?(\d+)\\\]",
            r"[p. \1]",
            text,
        )

        # 7. Images → numbered Markdown image syntax
        #    ![alt](any/path.ext)  →  ![image_N](images/image_N.png)
        #    Counter is local to this section (resets each call).
        _img_counter = [0]

        def _img(m: re.Match) -> str:
            _img_counter[0] += 1
            n = _img_counter[0]
            return f"![image_{n}](images/image_{n}.png)"

        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", _img, text)

        # 8. Unescape common pandoc backslash noise
        #    Handles \[ → [  and  \] → ]  which restores footnote markers,
        #    page markers already converted above, and other escaped punctuation.
        text = re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_{|}~`])", r"\1", text)

        # 9. Collapse 3+ consecutive blank lines to 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip() + "\n"
