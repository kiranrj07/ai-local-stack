# 02 — Architecture

## End-to-end data flow

```
build_index.py
   │
   ├── core/indexer.py        walk fs → chunk files w/ line meta
   │
   ├── core/ollama_client.py  POST /api/embeddings (in batches)
   │
   ├── faiss.IndexFlatIP      vectors normalized → cosine via IP
   │
   ├── rank_bm25.BM25Okapi    tokenized chunks → pickled
   │
   └── sqlite3                metadata.sqlite3 (chunk_id PK)
```

```
query_rag.py "question"
   │
   ├── core/router.py         resolve mode → ollama url + models
   │
   ├── core/retriever.py
   │      ├── vector_search   FAISS top_k by cosine
   │      ├── bm25_search     BM25 top_k by tokens
   │      ├── normalize→merge weighted 0.6 vector + 0.4 BM25
   │      └── (optional rerank via bge-reranker)
   │
   ├── build_prompt           context blocks w/ source headers
   │
   └── client.generate(...)   POST /api/generate to Ollama
          → answer w/ [path:start-end] citations
```

## Mode routing

`core.router.resolve_endpoint()` returns an `Endpoint` dataclass with `ollama_url`, model names, and a `fell_back` flag. Every script that needs an LLM/embedding endpoint asks the router — there are no hardcoded URLs anywhere except in the example IDE/agent configs.

## Security boundaries

| Boundary | Enforcement |
| --- | --- |
| Mac Ollama on 127.0.0.1 only | Verified by `check_system.sh`; warning if `*:11434` |
| Hybrid path is SSH-tunneled | `start_remote_ollama_tunnel.sh` uses `ssh -L 11435:localhost:11434`; no LAN exposure required |
| MCP filesystem | Restricted to `/Users/krajp/ai-local-stack` in `mcp_config.example.json` |
| No cloud APIs by default | `security.allow_cloud_apis: false` in `system.yaml`; no API keys configured |
| Network-required features | All marked disabled in MCP example config, called out in docs |

## On-disk layout

```
~/ai-local-stack/
├── .venv/                   Python 3.10-3.12 venv
├── config/                  system.yaml, rag_config.yaml, ...
├── core/                    router, indexer, retriever, ollama client
├── data/{raw,processed}/    Input docs and parsed markdown
├── docs/                    This documentation
├── indexes/
│   ├── faiss/vectors.faiss  cosine-normalized embeddings
│   ├── bm25/bm25.pkl        rank-bm25 pickled
│   └── metadata.sqlite3     chunk_id -> path, lines, text
├── logs/                    Tunnel log, RAG log, Phoenix output
├── scripts/                 Shell + Python entry points
└── tests/                   Sanity checks
```
