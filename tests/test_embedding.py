"""Sanity-check the embedding endpoint selected by core.router."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.ollama_client import OllamaClient
from core.router import resolve_endpoint


def test_embedding_returns_vector():
    ep = resolve_endpoint()
    if ep.embedding_provider != "ollama":
        # Only Ollama path is exercised in this minimal test.
        return
    client = OllamaClient(ep.ollama_url)
    vecs = client.embed(ep.embedding_model, ["hello world"])
    assert len(vecs) == 1
    assert len(vecs[0]) > 16, "embedding vector suspiciously short"


if __name__ == "__main__":
    test_embedding_returns_vector()
    print("test_embedding OK")
