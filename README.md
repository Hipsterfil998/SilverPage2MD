# BookMDBench

A benchmark dataset builder for document understanding tasks.
It downloads EPUB books from [Project Gutenberg](https://www.gutenberg.org/), converts them to Markdown (ground truth) and PDF (model input), samples pages across front/body/back sections, and renders them as JPEG images.

## Pipeline

1. Search and download EPUBs from Project Gutenberg
2. Convert EPUB → Markdown (ground truth) and PDF (model input)
3. Sample pages stratified across front / body / back zones
4. Render sampled PDF pages to JPEG images
5. Save aligned `(image, markdown)` pairs with metadata

## Dataset Parameters

| Parameter | Value |
|---|---|
| Languages | Italian, German |
| Books per language | 15 |
| Pages per book | 20 |
| Sampling strata | front: 5, body: 10, back: 5 |
| Image DPI | 150 |

## Installation

### 1. System dependencies

```bash
sudo apt-get install -y pandoc poppler-utils wkhtmltopdf
```

### 2. Python dependencies

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

Output will be saved to `./benchmark_data/`.

## Project Structure

```
book_mdBench/
├── book_mdBench/          # Python package (core logic)
│   ├── __init__.py
│   ├── config.py
│   ├── gutenberg_client.py
│   ├── epub_converter.py
│   ├── page_sampler.py
│   └── page_renderer.py
│
├── main.py                # Entry point
├── requirements.txt
└── README.md
```

## Output Structure

```
benchmark_data/
├── metadata.json
├── italian/
│   ├── metadata.json
│   └── <book_id>/
│       ├── book.epub
│       ├── book.md
│       ├── book.pdf
│       └── pages/
│           ├── page_0001.md
│           └── page_0001.jpg
└── german/
    └── ...
```
