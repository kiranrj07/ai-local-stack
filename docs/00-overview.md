# 00 — Overview

This stack gives you a private, dual-mode local AI coding + RAG setup with no cloud dependency by default.

## Components

| Layer | Tool | Where it runs |
| --- | --- | --- |
| LLM serving | Ollama 0.30.10 | Mac (local mode) or Ubuntu worker (hybrid) |
| Coder model | `qwen2.5-coder:14b` (fallback: `:7b`) | Wherever Ollama runs |
| Embedding model | `nomic-embed-text` via Ollama | Same as LLM |
| Reranker (opt) | `BAAI/bge-reranker-base` via sentence-transformers | Mac |
| Vector store | FAISS (faiss-cpu) | Mac disk |
| Keyword store | rank-bm25 (in-process) | Mac disk |
| Metadata | SQLite (`indexes/metadata.sqlite3`) | Mac disk |
| Exact search | ripgrep | Mac |
| Context compression | Headroom (optional) | Mac |
| Orchestration | Python (`core/router.py` + scripts) | Mac |
| IDE | VS Code + Continue or Cline | Mac |
| Refactor agent | Aider | Mac |
| Observability | Arize Phoenix (local) | Mac, port 6006 |

## Why both LlamaIndex and LangChain?

- **LlamaIndex** is the canonical RAG framework — chunking, vector stores, retrievers, schema.
- **LangChain** is used selectively where its Ollama wrappers or prompt utilities are cleaner.
- This stack ships a thin hand-rolled router (`core/router.py`) and a hand-rolled retriever (`core/retriever.py`) so the basics work without either library — both are available for richer pipelines.

## Mode boundary

`config/system.yaml` has `mode: local|hybrid`. Every script that talks to an LLM/embedding endpoint asks `core.router.resolve_endpoint()` for the URL. Switching modes is one file edit (or `bash scripts/switch_mode.sh`).

The router also handles **fallback**: if you're in hybrid and the worker is unreachable, it transparently falls back to local (configurable in `system.yaml` under `fallback:`).
