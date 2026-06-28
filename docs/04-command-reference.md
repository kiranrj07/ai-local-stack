# 04 — Command Reference

> Conventions: `${ROOT}` = `~/ai-local-stack`. Run inside `${ROOT}` unless noted.

## Shell scripts (under `scripts/`)

### `check_system.sh`
Read-only probe of Mac prerequisites: OS, CPU/RAM, presence of git/curl/python3/pip3/node/npm/npx/docker/rg/ollama, Ollama bind address, venv presence, index presence.
```bash
bash scripts/check_system.sh
```

### `check_remote_worker.sh`
Read-only probe of the Ubuntu worker over SSH: hostname, OS, arch, GPU, Ollama version + service state + bind address + model list.
```bash
bash scripts/check_remote_worker.sh
```

### `install_dependencies.sh`
Creates `.venv` (Python 3.10-3.12 via pyenv if available) and installs `requirements.txt`. Idempotent.

### `install_remote_worker.sh`
Interactive. Inspects the worker, then asks before installing missing apt packages, Ollama, or pulling models. Will not silently change the existing systemd Ollama config.

### `pull_models_local.sh` / `pull_models_remote.sh`
Pull `qwen2.5-coder:7b`, `qwen2.5-coder:14b`, `nomic-embed-text` (local also) on Mac / Ubuntu. Skips models already present.

### `switch_mode.sh {local|hybrid|status}`
Flips the top-level `mode:` line in `config/system.yaml` and prints router status.

### `start_remote_ollama_tunnel.sh`
Background `ssh -L 11435:localhost:11434 REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP` with ServerAlive keepalives. Idempotent — if the tunnel is already up, exits 0.

### `start_phoenix.sh`
Launches Phoenix on `http://localhost:6006`. Traces stored in `~/.phoenix`.

### `health_check.sh`
End-to-end: mac Ollama, remote Ollama via tunnel (if hybrid), index presence, venv + key imports, ripgrep, Phoenix.

## Python entry points (under `scripts/`)

### `build_index.py [--source PATH] [--config FILE] [--rebuild]`
Walks `source.dir`, chunks, embeds (via current router endpoint), writes FAISS + BM25 + SQLite.

### `query_rag.py "QUESTION" [--no-llm]`
Hybrid retrieval + LLM answer with citations. `--no-llm` prints retrieved hits only.

### `hybrid_search.py "QUERY" [--rg]`
Raw hybrid hits, or exact ripgrep search when `--rg`.

### `rerank_results.py`
Pipe-style. Reads `{"query": "...", "hits": [...]}` JSON on stdin, writes reranked JSON on stdout. Loads `BAAI/bge-reranker-base` on first run.

### `ingest_docs.py --input IN --output OUT`
Converts PDFs/HTML/DOCX in `IN` to Markdown in `OUT` using Docling or Unstructured (gracefully no-ops if neither is installed).

## One-liners

```bash
# Quick check that the active endpoint really works:
curl -s "$(python -c 'from core.router import resolve_endpoint; print(resolve_endpoint().ollama_url)')/api/tags" | jq .

# Top-K source citations only (no LLM call):
python scripts/query_rag.py "auth" --no-llm

# Re-index after a config change:
python scripts/build_index.py --rebuild
```
