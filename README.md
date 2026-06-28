# ai-local-stack

Local-first AI coding assistant + RAG environment with **two operating modes**:

- **Local mode** — everything runs on the Mac (Apple M4 Pro, 24 GB).
- **Hybrid mode** — Mac orchestrates; an Ubuntu worker (REPLACE_ME_WORKER_LAN_IP, RTX 4050) runs Ollama inference.
- **Auto mode (default)** — probe the worker; use it if reachable, otherwise transparently fall back to Mac.

> **Default is `auto`.** Nothing leaves the Mac unless the worker is reachable on your LAN. No cloud APIs are configured.

## What this stack does

- Runs Qwen-family coder models via **Ollama** for chat, completion, and RAG generation.
- Indexes any codebase or doc tree into **FAISS** (vectors) + **BM25** (keywords) with line-level metadata.
- Answers questions with **hybrid retrieval** (vector + BM25), optional **bge-reranker**, optional **Headroom** compression, with **source citations**.
- Drives **VS Code + Continue / Cline / Aider** against the same local or remote Ollama.
- Optional local observability via **Phoenix**.

## Architecture (text)

```
              ┌────────────── Mac (controller) ──────────────┐
              │  VS Code (Continue/Cline)   Aider            │
              │       │                                      │
              │       ▼                                      │
              │   ┌──────── Python RAG pipeline ────────┐    │
              │   │  build_index → FAISS + BM25 + meta  │    │
              │   │  query_rag   → hybrid retrieve      │    │
              │   │              + LLM via Ollama HTTP  │    │
              │   └──────────────────┬──────────────────┘    │
              │                      │                       │
              │   local mode ────────┘ http://localhost:11434│
              │                      │                       │
              └──────────────────────┼───────────────────────┘
                                     │ hybrid/auto mode
                                     │ ssh -L 11435:localhost:11434
                                     ▼
                         ┌─── Ubuntu 24 (REPLACE_ME_WORKER_LAN_IP) ───┐
                         │  Ollama   → RTX 4050 (6GB)      │
                         │           → CPU fallback        │
                         │  models: qwen2.5-coder:14b      │
                         │          nomic-embed-text       │
                         └─────────────────────────────────┘
```

## Quick start

```bash
# One-time setup
aitool install          # create venv, install Python deps
aitool pull-local       # pull qwen2.5-coder + nomic-embed-text on Mac
aitool index --rebuild  # build the RAG index

# Daily use
aitool status           # show resolved mode + endpoint
aitool query "What does the router do?"
```

Auto mode probes the Ubuntu worker (auto-opens SSH tunnel if configured) and falls back to local seamlessly. To force a mode:
```bash
aitool mode local       # never touch the worker
aitool mode hybrid      # require the worker (with fallback)
aitool mode auto        # default — let the router decide
```

## `aitool` CLI

The `aitool` command is installed at `~/.local/bin/aitool` (symlink to `~/ai-local-stack/bin/aitool`). Run from any directory.

| Command | What it does |
| --- | --- |
| `aitool --help` | Full command reference |
| `aitool status` | Show resolved mode + endpoint |
| `aitool mode <auto\|local\|hybrid>` | Switch operating mode |
| `aitool tunnel` / `aitool tunnel-stop` | Open / close SSH tunnel |
| `aitool check` / `aitool check-remote` / `aitool health` | Diagnostics |
| `aitool install` | Create `.venv` + install deps |
| `aitool pull-local` / `aitool pull-remote` | Pull Ollama models |
| `aitool index [--rebuild] [--source DIR]` | Build/rebuild FAISS+BM25 index |
| `aitool query "..."` | RAG question with citations |
| `aitool search [--rg] "..."` | Retrieval-only (or ripgrep) |
| `aitool ingest --input ... --output ...` | Parse PDFs/HTML/DOCX to Markdown |
| `aitool phoenix` | Start local Phoenix UI |
| `aitool shell` | Drop into venv-activated shell at project root |

## Privacy & security — read this first

- **Mac Ollama is bound to 127.0.0.1:11434** — verified at setup time. ✅
- **Ubuntu Ollama currently listens on all interfaces (`*:11434`).** See `docs/11-privacy-checklist.md` for hardening. Preferred fix: set `OLLAMA_HOST=127.0.0.1` on the worker and rely on the SSH tunnel.
- No cloud API key is configured. No code/embeddings/traces leave your network unless you enable an optional integration.
- MCP filesystem server is scoped to this project root only. Do **not** add `$HOME`.

See `docs/13-vscode-and-modes.md` for how `aitool query` coexists with VS Code agents like Cline.
