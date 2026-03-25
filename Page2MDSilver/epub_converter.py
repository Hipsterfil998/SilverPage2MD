"""
EPUB conversion utilities.

Parses an EPUB (ZIP) to extract HTML sections in spine order and converts
each section to clean Markdown for use as ground-truth labels.
"""

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath

from bs4 import BeautifulSoup
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
        html = self._promote_headings(html)
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

    # CSS class patterns → heading level (checked in order, first match wins).
    # Covers common Project Gutenberg class naming conventions for IT and DE.
    _HEADING_RULES: list[tuple[re.Pattern, int]] = [
        # Book / part title
        (re.compile(r"title|book.?head|tit(o(lo)?)?|titel", re.I), 1),
        # Chapter heading  (chap covers chaphead, pgchap, etc.)
        (re.compile(r"h1|chap|chapter|parte|part[^i]|capit|kapitel", re.I), 2),
        # Section heading
        (re.compile(r"h2|section|sezione|subchap|abschnitt|überschrift", re.I), 3),
        # Sub-section / paragraph heading
        (re.compile(r"h3|subsect|paragraph|paragrafo|absatz|unterab", re.I), 4),
        # Lower levels
        (re.compile(r"h[45]", re.I), 5),
    ]

    def _promote_headings(self, html: str) -> str:
        """Promote CSS-styled heading paragraphs to semantic <h1>–<h6> tags.

        Many old EPUB books (especially Project Gutenberg) use <p class="...">
        with visual CSS instead of semantic <h1>–<h6> elements.  Pandoc only
        converts semantic heading tags to # markers, so we normalise first.
        """
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(["p", "div", "span"]):
            classes = " ".join(tag.get("class") or [])
            if not classes:
                continue
            for pattern, level in self._HEADING_RULES:
                if pattern.search(classes):
                    # Only promote if the element is short (≤ 20 words) —
                    # long <p class="title"> blocks are likely not headings.
                    words = len(tag.get_text().split())
                    if words <= 20:
                        tag.name = f"h{level}"
                    break
        return str(soup)

    # ── cleaning ──────────────────────────────────────────────────────────────

    def _clean(self, text: str) -> str:
        """
        Post-process pandoc Markdown output to clean, standard Markdown.

        Removes pandoc-specific extensions and EPUB navigation noise:
          - YAML front matter, fenced divs  (::: … :::)
          - Span elements        [text]{.class}    →  text
          - Empty anchor spans   []{#id}           →  (removed)
          - Internal links       [text](#anchor)   →  text
          - Cross-file links     [text](path.xhtml)→  text  (preserves https://)
          - Footnote ref links   ^[[N]](url)^      →  [^N]
          - Bare number apice    ^N^               →  [^N]
          - Line blocks          | text            →  text  (pandoc verse ext.)
          - Leftover HTML tags

        Preserves / converts to standard Markdown:
          - Heading hierarchy (#, ##, ###), bold, italic, strikethrough ~~text~~
          - Superscript non-numerico ^text^ (extended MD standard)
          - Subscript ~text~ (extended MD standard)
          - Pipe tables, math ($…$, $$…$$), code blocks, blockquotes
          - Lists, hard line breaks (trailing backslash)
          - Images → ![image_N](images/image_N.png)  (numbered sequentially)
          - Page markers → [p. N]
          - Footnote markers [^N] and definitions [^N]: …
        """

        # 1. YAML front matter
        text = re.sub(r"^---\n.*?\n---\n?", "", text, flags=re.DOTALL)

        # 2. Pandoc fenced divs  ::: {#id .class} … :::
        text = re.sub(r"^:{3,}[^\n]*$", "", text, flags=re.MULTILINE)

        # 3. Heading links  ### [TITLE](#ref){attrs}  →  ### TITLE
        text = re.sub(
            r"^(#{1,6}[ \t]+)\[([^\]]+)\]\([^)]*\)([ \t]*\{[^}]*\})*",
            r"\1\2",
            text,
            flags=re.MULTILINE,
        )

        # 4a. Span elements  [text]{attrs}  →  text
        #     Handles multi-line content (centered blocks, small-caps, etc.).
        #     Must run BEFORE the generic {attrs} catch-all (step 5).
        text = re.sub(r"\[([^\]]+)\]\{[^}\n]{0,200}\}", r"\1", text)

        # 4b. Empty anchor spans  []{#id}  →  (remove)
        #     Must run before step 5 so the full []{} token is consumed.
        text = re.sub(r"\[\]\{[^}]*\}", "", text)

        # 4c. Internal anchor links  [text](#anchor)  →  text
        text = re.sub(r"\[([^\]\n]+)\]\(#[^)]*\)", r"\1", text)

        # 4d. Footnote ref links in superscript  ^[[N]](url)^  →  [^N]
        #     <sup><a href="#noteN">[N]</a></sup>  is the typical EPUB pattern.
        text = re.sub(r"\^\[\[(\d+)\]\]\([^)]*\)\^", r"[^\1]", text)

        # 4e. Remaining footnote ref links  [[N]](url)  →  [^N]
        #     Handles refs not wrapped in superscript.
        text = re.sub(r"\[\[(\d+)\]\]\([^)]*\)", r"[^\1]", text)

        # 4f. Superscript wrapper left around a footnote marker  ^[^N]^  →  [^N]
        #     Arises when step 4e ran but the outer ^…^ was not yet stripped.
        text = re.sub(r"\^\[\^(\d+)\]\^", r"[^\1]", text)

        # 4g. Bare number in superscript  ^N^  →  [^N]
        #     <sup>N</sup> without a link: treat as footnote reference.
        text = re.sub(r"\^(\d+)\^", r"[^\1]", text)

        # 4h. Cross-file EPUB links  [text](relative/path)  →  text
        #     Strips TOC / navigation / back-links; preserves https:// and mailto:.
        text = re.sub(
            r"\[([^\]\n]+)\]\((?!https?://|mailto:)[^)]+\)",
            r"\1",
            text,
        )

        # 4i. Residual [[N]] without URL  →  [^N]
        text = re.sub(r"\[\[(\d+)\]\]", r"[^\1]", text)

        # 4j. Bare empty brackets []
        text = re.sub(r"\[\]", "", text)

        # 4k. Line blocks  | text  →  text  (pandoc verse/line-block extension)
        #     Only strips lines whose sole | is the leading one (table rows
        #     contain multiple | and are left untouched).
        text = re.sub(r"^\| ([^|\n]+)$", r"\1", text, flags=re.MULTILINE)

        # 5. Generic inline attribute spans  {attrs}  (catch-all)
        text = re.sub(r"\{[^}\n]{0,200}\}", "", text)

        # 6. Leftover HTML tags  <div>, </span>, <br/>, etc.
        text = re.sub(r"<[^>\n]{0,200}>", "", text)

        # 7. Page number markers  \[pg!5\]  \[pg 5\]  \[Pg.5\]  →  [p. 5]
        text = re.sub(
            r"\\\[[Pp]g[!.\s]?(\d+)\\\]",
            r"[p. \1]",
            text,
        )

        # 8. Images → numbered Markdown image syntax
        #    ![alt](any/path.ext)  →  ![image_N](images/image_N.png)
        #    Counter is local to this section (resets each call).
        _img_counter = [0]

        def _img(m: re.Match) -> str:
            _img_counter[0] += 1
            n = _img_counter[0]
            return f"![image_{n}](images/image_{n}.png)"

        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", _img, text)

        # 9. Unescape pandoc backslash noise  \[ → [  \] → ]  etc.
        text = re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_{|}~`])", r"\1", text)

        # 10. Collapse 3+ consecutive blank lines to 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip() + "\n"
