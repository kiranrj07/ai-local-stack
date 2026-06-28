"""Hybrid retrieval: FAISS (vectors) + BM25 (keywords), merged + deduplicated."""
from __future__ import annotations

import json
import pickle
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .ollama_client import OllamaClient


@dataclass
class Hit:
    chunk_id: str
    rel_path: str
    ext: str
    start_line: int
    end_line: int
    text: str
    score: float
    source: str  # 'vector' | 'bm25' | 'hybrid'


def _load_metadata(db_path: Path) -> Dict[str, Dict]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT chunk_id, rel_path, ext, start_line, end_line, text FROM chunks").fetchall()
    finally:
        conn.close()
    return {
        r[0]: dict(chunk_id=r[0], rel_path=r[1], ext=r[2], start_line=r[3], end_line=r[4], text=r[5])
        for r in rows
    }


def vector_search(query: str, faiss_dir: Path, embedder, model: str, top_k: int) -> List[Tuple[str, float]]:
    import faiss
    import numpy as np
    index = faiss.read_index(str(faiss_dir / "vectors.faiss"))
    order = json.loads((faiss_dir / "chunk_order.json").read_text())
    emb = embedder.embed(model, [query])[0]
    arr = np.array([emb], dtype="float32")
    faiss.normalize_L2(arr)
    scores, idx = index.search(arr, top_k)
    out: List[Tuple[str, float]] = []
    for s, i in zip(scores[0].tolist(), idx[0].tolist()):
        if i < 0:
            continue
        out.append((order[i], float(s)))
    return out


def bm25_search(query: str, bm25_dir: Path, top_k: int) -> List[Tuple[str, float]]:
    with (bm25_dir / "bm25.pkl").open("rb") as fh:
        data = pickle.load(fh)
    bm25 = data["bm25"]
    ids = data["chunk_ids"]
    scores = bm25.get_scores(query.lower().split())
    ranked = sorted(zip(ids, scores), key=lambda x: x[1], reverse=True)[:top_k]
    return [(c, float(s)) for c, s in ranked]


def hybrid_retrieve(query: str, *, faiss_dir: Path, bm25_dir: Path, meta_db: Path,
                    embedder: OllamaClient, embedding_model: str,
                    vector_top_k: int, bm25_top_k: int, final_top_k: int) -> List[Hit]:
    v = vector_search(query, faiss_dir, embedder, embedding_model, vector_top_k)
    b = bm25_search(query, bm25_dir, bm25_top_k)

    # Normalize scores to [0,1] before merging
    def _norm(pairs: List[Tuple[str, float]]) -> Dict[str, float]:
        if not pairs:
            return {}
        scores = [s for _, s in pairs]
        lo, hi = min(scores), max(scores)
        if hi - lo < 1e-9:
            return {c: 1.0 for c, _ in pairs}
        return {c: (s - lo) / (hi - lo) for c, s in pairs}

    vn, bn = _norm(v), _norm(b)
    merged: Dict[str, float] = {}
    for c, s in vn.items():
        merged[c] = merged.get(c, 0.0) + 0.6 * s
    for c, s in bn.items():
        merged[c] = merged.get(c, 0.0) + 0.4 * s
    ranked = sorted(merged.items(), key=lambda x: x[1], reverse=True)[:final_top_k]

    metadata = _load_metadata(meta_db)
    hits: List[Hit] = []
    for cid, score in ranked:
        m = metadata.get(cid)
        if not m:
            continue
        src = "hybrid" if cid in vn and cid in bn else ("vector" if cid in vn else "bm25")
        hits.append(Hit(
            chunk_id=cid,
            rel_path=m["rel_path"],
            ext=m["ext"],
            start_line=m["start_line"],
            end_line=m["end_line"],
            text=m["text"],
            score=score,
            source=src,
        ))
    return hits
