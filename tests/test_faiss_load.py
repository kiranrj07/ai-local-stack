"""Verify the FAISS index loads and answers a nearest-neighbour query."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_faiss_load():
    import faiss
    import numpy as np

    faiss_dir = ROOT / "indexes" / "faiss"
    if not (faiss_dir / "vectors.faiss").exists():
        print("skip: no FAISS index. Run scripts/build_index.py first.")
        return

    index = faiss.read_index(str(faiss_dir / "vectors.faiss"))
    order = json.loads((faiss_dir / "chunk_order.json").read_text())
    assert index.ntotal == len(order), "FAISS ntotal vs chunk_order mismatch"
    assert index.ntotal > 0

    # Random unit vector query to confirm search works
    rng = np.random.default_rng(42)
    q = rng.standard_normal((1, index.d), dtype="float32")
    faiss.normalize_L2(q)
    D, I = index.search(q, 3)
    assert D.shape == (1, 3) and I.shape == (1, 3)


if __name__ == "__main__":
    test_faiss_load()
    print("test_faiss_load OK")
