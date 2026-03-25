<div align="center">

# SilverPage2MD

</div>

A **silver standard generator** for multilingual PDF-to-Markdown conversion benchmarking.

It downloads EPUB books from [Project Gutenberg](https://www.gutenberg.org/) and supports any language available in its catalogue (Italian, German, English, French, Spanish, Portuguese, and more). Each section is converted to clean Markdown, split into page-sized chunks, and rendered as a JPEG image via LaTeX.

> **Silver standard note:** The ground truth produced by this pipeline is a *silver* standard, automatically derived rather than manually annotated. The benchmark is **literary in nature**: all source material comes from Project Gutenberg and consists of prose, poetry, and essays, with little to no mathematical notation, charts, or technical/scientific content. The size of the benchmark scales with the number of languages included and the computational resources available to run the prediction models. Adding more languages increases dataset coverage but also raises rendering and inference costs proportionally.

## Pipeline

1. Search and download EPUBs from Project Gutenberg
2. Parse EPUB spine → extract HTML sections in reading order
3. Convert each HTML section → clean Markdown (silver standard)
4. Split sections into page-sized chunks:
   - primary: split at `[p. N]` markers (original book pagination)
   - fallback: split into ~2800-char blocks at paragraph boundaries
5. Sample chunks stratified across front / body / back zones
6. Render each sampled chunk to JPEG (`chunk.md → PDF (xelatex) → JPEG`)
7. Save aligned `(image, markdown)` pairs with metadata

Since both the JPEG and the Markdown come from the same source text, image and silver standard reference always represent exactly the same content.

## Markdown Silver Standard

Each `.md` file preserves:

| Element | Format |
|---|---|
| Heading hierarchy | `#` `##` `###` `####` |
| Bold / Italic / Bold+italic | `**text**` / `*text*` / `***text***` |
| Tables | GFM pipe tables with `---` separator row |
| Math | `$...$` inline, `$$...$$` block |
| Unordered / Ordered lists | `- item` / `1. item` |
| Images | `![alt](images/filename.ext)` |
| Book page numbers | `[p. N]` |
| Footnote markers | `[^N]` inline references |
| Footnote definitions | `[^N]: text` |
| Blockquotes | `> text` |

## Dataset Parameters

| Parameter | Value |
|---|---|
| Languages | Italian, German |
| Books per language | 1 (`N_BOOKS` in `config.py`) |
| Pages per book | 20 |
| Mandatory frontmatter pages | 3 |
| Sampling strata | front: 2, body: 10, back: 5 |
| Image DPI | 200 |
| JPEG quality | 92 |

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Hipsterfil998/SilverPage2MD.git
cd SilverPage2MD
```

### 2. System dependencies

```bash
sudo apt-get install -y pandoc poppler-utils texlive-xetex texlive-lang-italian texlive-lang-german
```

On Google Colab:

```python
!apt-get update -q
!apt-get install -y pandoc poppler-utils texlive-xetex texlive-lang-italian texlive-lang-german
!pip install -r requirements.txt -q
```

### 3. Python dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `predict.py` additionally requires [vLLM](https://docs.vllm.ai/en/latest/getting_started/installation.html) and a CUDA-capable GPU:
> ```bash
> pip install vllm
> ```

## Usage

### Build the dataset

```bash
python BenchmarkBuilder.py
```

Output will be saved to `./dataset/`.

### Generate predictions

In a Colab notebook:

```python
from predict import PageImagePredictor
from pathlib import Path

PRED_DIR = Path("predictions")

for MODEL in [
    "Qwen/Qwen2.5-VL-7B-Instruct",
    "mistralai/Pixtral-12B-2409",
]:
    p = PageImagePredictor(model_id=MODEL)
    p.predict_dataset(Path("dataset"), PRED_DIR / p.model_slug)
```

Each model's predictions are saved under `predictions/<model-slug>/` so runs never overwrite each other.

### Evaluate predictions

Single pair:

```bash
python eval.py ground_truth.md prediction.md
```

Batch (all `.md` files in a directory):

```bash
python eval.py --ref-dir dataset/italian/book_123/pages \
               --pred-dir predictions/Qwen2.5-VL-7B-Instruct/italian/book_123
```

Add `--bert` to also compute BERTScore (downloads ~1 GB model on first run):

```bash
python eval.py --ref-dir ... --pred-dir ... --bert
```

## Metrics

| Metric | Range | Better |
|---|---|---|
| NED (Normalised Edit Distance) | [0, 1] | lower |
| BLEU | [0, 100] | higher |
| Structure F1 | [0, 1] | higher |
| BERTScore (opt-in) | [0, 1] | higher |

**Structure F1** measures precision/recall over 13 structural Markdown element types. AST-extracted (via mistune): headings, tables, images, list items, blockquotes. Regex-extracted: block math `$$...$$`, inline math `$...$`, page numbers `[p. N]`, footnote markers `[^N]`, footnote definitions `[^N]: ...`, bold `**...**`, italic `*...*`, bold+italic `***...***`. The overall score is a macro-average F1 across element types present in the reference.

**BERTScore** uses `xlm-roberta-base` for multilingual semantic similarity.

## Project Structure

```
SilverPage2MD/
├── BenchmarkBuilder.py    # Entry point — builds the dataset
├── eval.py                # Evaluation script
├── predict.py             # Prediction script (VLM via vLLM)
├── config.py              # Global parameters
│
├── Page2MDSilver/         # Dataset construction pipeline
│   ├── gutenberg_client.py  # Project Gutenberg search + EPUB download
│   ├── epub_converter.py    # EPUB spine parsing + HTML → Markdown
│   ├── page_sampler.py      # Chunk splitting + stratified sampling
│   └── page_renderer.py     # Markdown → PDF (xelatex) → JPEG
│
└── metrics/               # Evaluation metrics
    ├── _utils.py            # Shared text normalisation
    ├── ned.py               # Normalised Edit Distance
    ├── bleu.py              # BLEU score (sacrebleu)
    ├── md_structure.py      # Markdown Structure F1 (mistune)
    └── bertscore.py         # BERTScore (xlm-roberta-base)
```

## Output Structure

```
dataset/
├── metadata.json
├── italian/
│   ├── metadata.json
│   └── <book_id>_<title>/
│       ├── book.epub
│       ├── book.md          # full book Markdown
│       └── pages/
│           ├── page_0001.md
│           └── page_0001.jpg
└── german/
    └── ...
```

## Citation

If you use this work, please cite:

```bibtex
@misc{pellegrino2026silverpage2md,
  author       = {Pellegrino, Filippo},
  title        = {SilverPage2MD: A Silver Standard Generator for Multilingual PDF-to-Markdown Benchmarking},
  year         = {2026},
  howpublished = {\url{https://github.com/Hipsterfil998/Page2MDBench}}
}
```
