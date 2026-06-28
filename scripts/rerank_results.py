#!/usr/bin/env python3
"""Stand-alone reranker. Reads JSON hits on stdin, writes reranked JSON on stdout.

Input format (one JSON object):
    {"query": "...", "hits": [{"chunk_id": "...", "text": "..."}, ...]}

Requires sentence-transformers + bge-reranker-base (downloaded on first run).
"""
from __future__ import annotations

import json
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        print(f"invalid JSON on stdin: {exc}", file=sys.stderr)
        return 2

    query = payload["query"]
    hits = payload["hits"]
    if not hits:
        json.dump({"hits": []}, sys.stdout)
        return 0

    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        print("sentence-transformers not installed", file=sys.stderr)
        return 3

    ce = CrossEncoder("BAAI/bge-reranker-base")
    pairs = [(query, h["text"]) for h in hits]
    scores = ce.predict(pairs).tolist()
    for h, s in zip(hits, scores):
        h["rerank_score"] = float(s)
    hits.sort(key=lambda h: h["rerank_score"], reverse=True)
    json.dump({"hits": hits}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
