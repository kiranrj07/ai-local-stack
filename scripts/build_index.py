#!/usr/bin/env python3
"""Build the local RAG index: FAISS (vectors) + BM25 (keywords) + SQLite metadata.

Usage:
    python scripts/build_index.py --source . --config config/rag_config.yaml
"""
from __future__ import annotations

import argparse
import json
import pickle
import sqlite3
import sys
import time
from pathlib import Path
from typing import List

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.indexer import Chunk, chunk_file, iter_source_files  # noqa: E402
from core.ollama_client import OllamaClient  # noqa: E402
from core.router import load_system_config, resolve_endpoint  # noqa: E402


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=None, help="Override source dir from rag_config.yaml")
    ap.add_argument("--config", default="config/rag_config.yaml")
    ap.add_argument("--rebuild", action="store_true", help="Wipe existing index first")
    return ap.parse_args()


def load_rag_config(path: Path):
    with path.open() as fh:
        return yaml.safe_load(fh)


def write_bm25(chunks: List[Chunk], out_dir: Path) -> None:
    from rank_bm25 import BM25Okapi
    out_dir.mkdir(parents=True, exist_ok=True)
    tokenized = [c.text.lower().split() for c in chunks]
    bm25 = BM25Okapi(tokenized)
    with (out_dir / "bm25.pkl").open("wb") as fh:
        pickle.dump({"bm25": bm25, "chunk_ids": [c.chunk_id for c in chunks]}, fh)


def write_faiss(chunks: List[Chunk], embeddings, out_dir: Path) -> None:
    import faiss
    import numpy as np
    out_dir.mkdir(parents=True, exist_ok=True)
    arr = np.array(embeddings, dtype="float32")
    # Normalize so we can use inner product as cosine similarity
    faiss.normalize_L2(arr)
    index = faiss.IndexFlatIP(arr.shape[1])
    index.add(arr)
    faiss.write_index(index, str(out_dir / "vectors.faiss"))
    with (out_dir / "chunk_order.json").open("w") as fh:
        json.dump([c.chunk_id for c in chunks], fh)


def write_metadata_sqlite(chunks: List[Chunk], db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE chunks (
            chunk_id TEXT PRIMARY KEY,
            rel_path TEXT NOT NULL,
            ext TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            text TEXT NOT NULL
        )
    """)
    conn.executemany(
        "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?)",
        [(c.chunk_id, c.rel_path, c.ext, c.start_line, c.end_line, c.text) for c in chunks],
    )
    conn.execute("CREATE INDEX idx_path ON chunks(rel_path)")
    conn.commit()
    conn.close()


def embed_with_ollama(client: OllamaClient, model: str, chunks: List[Chunk]) -> List[List[float]]:
    # Batch by progress print; Ollama embeddings API is single-text per call.
    out: List[List[float]] = []
    total = len(chunks)
    t0 = time.time()
    for i, c in enumerate(chunks, 1):
        out.extend(client.embed(model, [c.text]))
        if i % 25 == 0 or i == total:
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            print(f"  embedded {i}/{total}  ({rate:.1f} chunks/s)", flush=True)
    return out


def embed_with_hf(model_name: str, chunks: List[Chunk]) -> List[List[float]]:
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(model_name)
    return m.encode([c.text for c in chunks], show_progress_bar=True, convert_to_numpy=True).tolist()


def main() -> int:
    args = parse_args()
    rag_cfg = load_rag_config(ROOT / args.config)
    sys_cfg = load_system_config()
    ep = resolve_endpoint(sys_cfg)

    print(f"[build_index] mode={ep.mode} ollama={ep.ollama_url} "
          f"embedding={ep.embedding_provider}:{ep.embedding_model}", flush=True)
    if ep.fell_back:
        print(f"[build_index] WARNING: {ep.reason}", flush=True)

    source = Path(args.source or rag_cfg["source"]["dir"]).resolve()
    if not source.exists():
        print(f"source dir does not exist: {source}", file=sys.stderr)
        return 2
    print(f"[build_index] source = {source}", flush=True)

    files = list(iter_source_files(
        source,
        rag_cfg["include_extensions"],
        rag_cfg["exclude_dirs"],
        rag_cfg["source"]["min_bytes"],
        rag_cfg["source"]["max_bytes"],
    ))
    print(f"[build_index] {len(files)} files to index", flush=True)

    chunks: List[Chunk] = []
    for p in files:
        chunks.extend(chunk_file(p, source,
                                 rag_cfg["chunking"]["chunk_size"],
                                 rag_cfg["chunking"]["chunk_overlap"]))
    print(f"[build_index] {len(chunks)} chunks total", flush=True)
    if not chunks:
        print("nothing to index. check include_extensions / source dir.", file=sys.stderr)
        return 3

    # Wipe existing if --rebuild
    if args.rebuild:
        for sub in ("faiss", "bm25"):
            d = ROOT / "indexes" / sub
            if d.exists():
                for f in d.iterdir():
                    f.unlink()
        meta = ROOT / rag_cfg["storage"]["metadata_db"]
        if meta.exists():
            meta.unlink()

    # Embed
    if ep.embedding_provider == "ollama":
        client = OllamaClient(ep.ollama_url)
        embeddings = embed_with_ollama(client, ep.embedding_model, chunks)
    elif ep.embedding_provider == "huggingface":
        embeddings = embed_with_hf(ep.embedding_model, chunks)
    else:
        print(f"unknown embedding_provider: {ep.embedding_provider}", file=sys.stderr)
        return 4

    print("[build_index] writing FAISS index", flush=True)
    write_faiss(chunks, embeddings, ROOT / rag_cfg["storage"]["faiss_dir"])

    print("[build_index] writing BM25 index", flush=True)
    write_bm25(chunks, ROOT / rag_cfg["storage"]["bm25_dir"])

    print("[build_index] writing metadata SQLite", flush=True)
    write_metadata_sqlite(chunks, ROOT / rag_cfg["storage"]["metadata_db"])

    print(f"[build_index] DONE — {len(files)} files, {len(chunks)} chunks", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
