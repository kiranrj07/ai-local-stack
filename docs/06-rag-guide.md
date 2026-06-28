# 06 — RAG Guide

## Chunking

`core/indexer.py` does line-aware chunking. Default: `chunk_size=1000` chars, `chunk_overlap=200`. Each chunk records:
- `chunk_id`  (`<rel_path>::<idx>`)
- `rel_path`, `ext`, `start_line`, `end_line`, `text`

Stored in SQLite (`indexes/metadata.sqlite3`) so retrieval doesn't need to re-read source files.

## Embeddings

Default: `nomic-embed-text` via Ollama (`/api/embeddings`). One vector per chunk. 768-dim.

Switch to HuggingFace `bge-base-en-v1.5` by setting `embedding_provider: huggingface` in `system.yaml`. The build script will then use `sentence-transformers` in-process — slower first run (downloads weights) but no extra Ollama load.

## FAISS

`IndexFlatIP` over L2-normalized vectors. Cosine similarity = inner product after normalization. Stored as `indexes/faiss/vectors.faiss` + `chunk_order.json` (id ordering).

`IndexFlatIP` is exact (no approximation) and adequate up to a few hundred thousand chunks. For larger corpora switch to `IndexHNSWFlat` or `IndexIVFFlat` — both are 1-line changes in `build_index.py`.

## BM25

`rank-bm25` BM25Okapi, default parameters. Tokenization: lowercase + whitespace split (deliberately simple; you can swap to a smarter tokenizer if you need to handle CamelCase or punctuation aggressively).

## Reranking

Off by default. Enable in `config/rag_config.yaml`:
```yaml
retrieval:
  rerank: true
```
Uses `BAAI/bge-reranker-base` cross-encoder. First run downloads ~1 GB to the HF cache. Adds ~200-500 ms per query but materially improves precision on code search.

## Hybrid search

`core/retriever.py::hybrid_retrieve`:
1. Vector top-k (default 8)
2. BM25 top-k (default 8)
3. Normalize each list to [0,1]
4. Weighted merge: 0.6 × vector + 0.4 × BM25
5. (Optional) rerank
6. Return final top-k (default 5)

Tune the 0.6/0.4 split in `core/retriever.py` — `vector` weighted higher works well for code (semantic similarity matters), `bm25` weighted higher works better for log/text search.

## Context compression (Headroom)

Off by default. When enabled in `config/rag_config.yaml`:
```yaml
retrieval:
  compression:
    enabled: true
    min_chars_to_compress: 6000
```

Skipped when retrieved context is small. **Never** compresses:
- security-sensitive diffs
- short config snippets
- short code patches

Used for:
- long log dumps
- many big chunks
- conversation history

## Source citations

`query_rag.py` prompts the model to cite as `[path:start-end]`. The system prompt is strict — if the model can't justify an answer from context, it must say so. Trust this more than absence of warnings; the model occasionally hallucinates fluent prose.
