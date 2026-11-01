# OCR & Document Text Extraction (merged from the ocr-and-documents skill)

Scripts referenced below live in this skill's scripts/ directory.
# PDF & Document Extraction

For DOCX: see the `docx` skill (create/edit) or use `python-docx` for structured reads.
For PPTX: see the `powerpoint` skill (full create/read/edit support).
For PDF manipulation (merge, split, forms, watermarks, creation): see the `pdf` skill.
This skill covers **text extraction from PDFs and scanned documents**.

> **Coming from a `read` EXTRACTION COVERAGE WARNING?** `read` auto-converts local PDFs but reads the text layer only; the warning footer lists the pages that yielded no text (scanned images). For a handful of pages, render + vision is fastest: `python scripts/pdf_page_image.py file.pdf --pages N --dpi 150 --out-dir $TMPDIR/pages` then read each PNG with the `read` tool and transcribe what you see. For bulk OCR of many pages, use marker-pdf below (Step 2).

## Step 1: Remote URL Available?

If the document has a URL, **always try `web_extract` first**:

```
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])
web_extract(urls=["https://example.com/report.pdf"])
```

This handles PDF-to-markdown conversion via Firecrawl with no local dependencies.

Only use local extraction when: the file is local, web_extract fails, or you need batch processing.

## Step 2: Choose Local Extractor

| Need | Use |
|------|-----|
| **Text-based PDF** (has a text layer) | `python scripts/pdf_read.py document.pdf --text` (pdfplumber, instant) |
| **Tables** | `python scripts/pdf_read.py document.pdf --tables --csv-dir t/` |
| **Title, author, pages, scanned flag** | `python scripts/pdf_read.py document.pdf --meta` |
| **Scanned / image-only pages** | render with `pdf_page_image.py`, then read the images (below) |
| **Bulk OCR, equations, complex layout** | marker-pdf (~3-5GB, optional, below) |

**Decision**: read the text layer first. Render image-only pages and read them with native image reading. Also render dense plans, diagrams and mixed visual/text schedules even when text extraction succeeds. Follow the PDF skill's source-coverage procedure to reconcile labels, legends and room assignments; nonempty extracted text is not complete spatial understanding.

## Scanned pages: render, then read the image

```bash
python scripts/pdf_page_image.py scanned.pdf --pages 1-3 --dpi 150 --out-dir pages/
```

This writes `pages/page001.png` and so on (pypdfium2, no models). Open each PNG with the `read` tool and transcribe the text, tables and figures you see. Use `--dpi 200` for small print. This works for any language and needs nothing installed beyond the skill.

If the user needs marker capabilities for many pages but the system lacks ~5GB free disk:
> "This document needs bulk OCR (marker-pdf), which requires ~5GB for PyTorch and models. Your system has [X]GB free. Options: free up space, provide a URL so I can fetch it, or I can read the pages as images one by one."

---

## marker-pdf (high-quality OCR)

```bash
# Check disk space first
python scripts/extract_marker.py --check

pip install marker-pdf
```

**Via helper script**:
```bash
python scripts/extract_marker.py document.pdf                # Markdown
python scripts/extract_marker.py document.pdf --json         # JSON with metadata
python scripts/extract_marker.py document.pdf --output_dir out/  # Save images
python scripts/extract_marker.py scanned.pdf                 # Scanned PDF (OCR)
python scripts/extract_marker.py document.pdf --use_llm      # LLM-boosted accuracy
```

**CLI** (installed with marker-pdf):
```bash
marker_single document.pdf --output_dir ./output
marker /path/to/folder --workers 4    # Batch
```

---

## Arxiv Papers

```
# Abstract only (fast)
web_extract(urls=["https://arxiv.org/abs/2402.03300"])

# Full paper
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])

# Search
web_search(query="arxiv GRPO reinforcement learning 2026")
```

## Split, Merge & Search

Use the pdf skill scripts: `pdf_split.py doc.pdf --pages 1-5 -o part.pdf`, `pdf_merge.py a.pdf b.pdf -o merged.pdf`, and `pdf_read.py doc.pdf --text` then search the JSON it prints.

---

## Notes

- `web_extract` is always first choice for URLs
- `pdf_read.py --text` is the safe default for text PDFs; `pdf_page_image.py` + reading the images covers scans
- marker-pdf is for OCR, scanned docs, equations, complex layouts — install only when needed
- Both helper scripts accept `--help` for full usage
- marker-pdf downloads ~2.5GB of models to `~/.cache/huggingface/` on first use
- For Word docs: `pip install python-docx` (better than OCR — parses actual structure)
- For PowerPoint: see the `powerpoint` skill (uses python-pptx)
