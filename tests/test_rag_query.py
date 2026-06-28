"""End-to-end retrieval test (no LLM call). Skips gracefully if no index."""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.ollama_client import OllamaClient
from core.retriever import hybrid_retrieve
from core.router import resolve_endpoint


def test_hybrid_retrieve_returns_hits():
    rag = yaml.safe_load((ROOT / "config/rag_config.yaml").read_text())
    faiss_dir = ROOT / rag["storage"]["faiss_dir"]
    if not (faiss_dir / "vectors.faiss").exists():
        print("skip: no FAISS index. Run scripts/build_index.py first.")
        return

    ep = resolve_endpoint()
    client = OllamaClient(ep.ollama_url)
    hits = hybrid_retrieve(
        "configuration",
        faiss_dir=faiss_dir,
        bm25_dir=ROOT / rag["storage"]["bm25_dir"],
        meta_db=ROOT / rag["storage"]["metadata_db"],
        embedder=client,
        embedding_model=ep.embedding_model,
        vector_top_k=rag["retrieval"]["vector_top_k"],
        bm25_top_k=rag["retrieval"]["bm25_top_k"],
        final_top_k=rag["retrieval"]["final_top_k"],
    )
    assert hits, "hybrid_retrieve returned no hits"
    for h in hits:
        assert h.rel_path
        assert h.start_line <= h.end_line


if __name__ == "__main__":
    test_hybrid_retrieve_returns_hits()
    print("test_rag_query OK")
