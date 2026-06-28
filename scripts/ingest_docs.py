#!/usr/bin/env python3
"""Ingest external documents (PDFs, HTML, markdown) into data/processed.

Falls back gracefully when optional parsers (docling, unstructured) aren't installed.

Usage:
    python scripts/ingest_docs.py --input data/raw --output data/processed
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


SUPPORTED_RAW = {".pdf", ".html", ".htm", ".md", ".txt", ".docx", ".pptx"}


def _try_docling(path: Path) -> str | None:
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        return None
    conv = DocumentConverter()
    res = conv.convert(str(path))
    return res.document.export_to_markdown()


def _try_unstructured(path: Path) -> str | None:
    try:
        from unstructured.partition.auto import partition
    except ImportError:
        return None
    elems = partition(filename=str(path))
    return "\n\n".join(str(e) for e in elems)


def _read_plain(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def convert(path: Path) -> str:
    if path.suffix.lower() in {".md", ".txt"}:
        return _read_plain(path)
    for fn in (_try_docling, _try_unstructured):
        out = fn(path)
        if out is not None:
            return out
    raise RuntimeError(
        f"Cannot parse {path.suffix} without docling or unstructured. "
        "Install one of them or skip."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    in_dir = Path(args.input).resolve()
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not in_dir.exists():
        print(f"input dir not found: {in_dir}", file=sys.stderr)
        return 2

    converted = 0
    skipped = 0
    for p in in_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in SUPPORTED_RAW:
            continue
        try:
            md = convert(p)
        except Exception as exc:
            print(f"  SKIP {p.name}: {exc}", file=sys.stderr)
            skipped += 1
            continue
        target = out_dir / (p.stem + ".md")
        target.write_text(md, encoding="utf-8")
        converted += 1
        print(f"  OK {p.name} -> {target.name}")

    print(f"converted={converted} skipped={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
