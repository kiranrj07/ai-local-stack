#!/usr/bin/env python3
"""Hybrid RAG query.

Usage:
    python scripts/query_rag.py "Where is authentication handled?"
"""
from __future__ import annotations

import os
# Workaround for macOS OpenMP runtime conflict between faiss-cpu and pytorch.
# Both link libomp; this allows the second runtime to load without aborting.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.ollama_client import OllamaClient  # noqa: E402
from core.retriever import hybrid_retrieve  # noqa: E402
from core.router import load_system_config, resolve_endpoint  # noqa: E402
from core.tracing import setup_tracing, trace_span  # noqa: E402


SYSTEM_PROMPT = """You are a careful code/doc assistant. Answer only from the provided context.

Rules:
- If the answer is not in the context, say "I don't know from the indexed sources."
- Always cite source files as: [path:start_line-end_line].
- Prefer concise answers (4-8 lines) unless the question requires more.
- After the answer, output a confidence (low/medium/high) and one suggested next command.
"""


def build_prompt(question: str, hits) -> str:
    lines = ["# Context", ""]
    for h in hits:
        lines.append(f"## {h.rel_path}:{h.start_line}-{h.end_line}  (score={h.score:.3f}, via={h.source})")
        lines.append("```")
        lines.append(h.text.rstrip())
        lines.append("```")
        lines.append("")
    lines.append("# Question")
    lines.append(question)
    lines.append("")
    lines.append("# Answer (cite as [path:start-end]):")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="+", help="Question to ask")
    ap.add_argument("--config", default="config/rag_config.yaml")
    ap.add_argument("--no-llm", action="store_true", help="Only print retrieved hits, skip LLM call")
    args = ap.parse_args()
    question = " ".join(args.question)

    rag_cfg = yaml.safe_load((ROOT / args.config).read_text())
    sys_cfg = load_system_config()
    ep = resolve_endpoint(sys_cfg)

    print(f"[query_rag] mode={ep.mode}  endpoint={ep.ollama_url}", file=sys.stderr)
    if ep.fell_back:
        print(f"[query_rag] FALLBACK: {ep.reason}", file=sys.stderr)

    tracing_on = setup_tracing()
    if tracing_on:
        print("[query_rag] Phoenix tracing ON (http://localhost:6006)", file=sys.stderr)

    client = OllamaClient(ep.ollama_url)

    faiss_dir = ROOT / rag_cfg["storage"]["faiss_dir"]
    bm25_dir = ROOT / rag_cfg["storage"]["bm25_dir"]
    meta_db = ROOT / rag_cfg["storage"]["metadata_db"]

    if not (faiss_dir / "vectors.faiss").exists():
        print("FAISS index not found. Run: python scripts/build_index.py", file=sys.stderr)
        return 2

    with trace_span("retrieve", query=question, mode=ep.mode):
        hits = hybrid_retrieve(
            question,
            faiss_dir=faiss_dir,
            bm25_dir=bm25_dir,
            meta_db=meta_db,
            embedder=client,
            embedding_model=ep.embedding_model,
            vector_top_k=rag_cfg["retrieval"]["vector_top_k"],
            bm25_top_k=rag_cfg["retrieval"]["bm25_top_k"],
            final_top_k=rag_cfg["retrieval"]["final_top_k"],
            rerank=rag_cfg["retrieval"].get("rerank", False),
            reranker_model=ep.reranker_model or "BAAI/bge-reranker-base",
        )

    print("\n=== Retrieved context ===", file=sys.stderr)
    for h in hits:
        print(f"  {h.rel_path}:{h.start_line}-{h.end_line}  score={h.score:.3f}  via={h.source}",
              file=sys.stderr)

    if args.no_llm:
        return 0

    prompt = build_prompt(question, hits)
    llm_model = rag_cfg["generation"].get("override_llm_model") or ep.llm_model

    with trace_span("generate", model=llm_model, mode=ep.mode):
        answer = client.generate(
            llm_model,
            prompt,
            system=SYSTEM_PROMPT,
            temperature=rag_cfg["generation"]["temperature"],
            num_predict=rag_cfg["generation"]["max_output_tokens"],
        )

    print("\n=== Answer ===")
    print(answer.strip())
    print("\n=== Relevant files ===")
    seen = set()
    for h in hits:
        if h.rel_path not in seen:
            print(f"  {h.rel_path}  (lines {h.start_line}-{h.end_line}, via {h.source})")
            seen.add(h.rel_path)
    print(f"\n=== Endpoint ===\n  mode={ep.mode}  model={llm_model}  url={ep.ollama_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
