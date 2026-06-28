#!/usr/bin/env python3
"""Hybrid search without LLM generation. Shows raw retrieval hits.

Usage:
    python scripts/hybrid_search.py "specific function or error"
    python scripts/hybrid_search.py --rg "exact string"      # ripgrep exact search
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.ollama_client import OllamaClient  # noqa: E402
from core.retriever import hybrid_retrieve  # noqa: E402
from core.router import load_system_config, resolve_endpoint  # noqa: E402


def run_ripgrep(query: str, source_dir: Path) -> int:
    rg = shutil.which("rg")
    if not rg:
        print("ripgrep (rg) not found. brew install ripgrep", file=sys.stderr)
        return 127
    print(f"[ripgrep] {rg} -n -S {query!r} in {source_dir}", file=sys.stderr)
    return subprocess.call([rg, "-n", "-S", query, str(source_dir)])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="+")
    ap.add_argument("--config", default="config/rag_config.yaml")
    ap.add_argument("--rg", action="store_true", help="Use ripgrep for exact match instead of hybrid")
    args = ap.parse_args()
    query = " ".join(args.query)

    rag_cfg = yaml.safe_load((ROOT / args.config).read_text())

    if args.rg:
        return run_ripgrep(query, Path(rag_cfg["source"]["dir"]).resolve())

    sys_cfg = load_system_config()
    ep = resolve_endpoint(sys_cfg)
    client = OllamaClient(ep.ollama_url)

    hits = hybrid_retrieve(
        query,
        faiss_dir=ROOT / rag_cfg["storage"]["faiss_dir"],
        bm25_dir=ROOT / rag_cfg["storage"]["bm25_dir"],
        meta_db=ROOT / rag_cfg["storage"]["metadata_db"],
        embedder=client,
        embedding_model=ep.embedding_model,
        vector_top_k=rag_cfg["retrieval"]["vector_top_k"],
        bm25_top_k=rag_cfg["retrieval"]["bm25_top_k"],
        final_top_k=rag_cfg["retrieval"]["final_top_k"],
    )
    for h in hits:
        print(f"--- {h.rel_path}:{h.start_line}-{h.end_line}  score={h.score:.3f}  via={h.source}")
        snippet = h.text.strip().splitlines()[:8]
        for line in snippet:
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
