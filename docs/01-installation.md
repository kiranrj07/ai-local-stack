# 01 — Installation

Tested on macOS 26.5.1 (M4 Pro, 24 GB) controller + Ubuntu 24.04 (RTX 4050) worker.

## 1. Mac prerequisites

Run the probe — read-only, installs nothing:
```bash
bash scripts/check_system.sh
```

What you should have:
- Homebrew + `python3` (3.10-3.12 preferred; 3.14 doesn't have wheels for `faiss-cpu` yet)
- `ollama` (0.30+), running and bound to `127.0.0.1:11434`
- `node` + `npm` (for MCP servers and Cline)
- `rg` (ripgrep)
- `git`, `curl`, `docker` (optional)

Install missing pieces with:
```bash
brew install ripgrep ollama node
brew install pyenv && pyenv install 3.11.9
```

## 2. Python environment

```bash
bash scripts/install_dependencies.sh    # creates .venv, installs requirements.txt
source .venv/bin/activate
```

If your system Python is 3.14 (Homebrew default as of this writing), the script picks up `pyenv` 3.10–3.12 automatically.

## 3. Pull models locally

```bash
bash scripts/pull_models_local.sh
```

Pulls (skipped if already present):
- `qwen2.5-coder:7b` (~4.7 GB) — fast everyday
- `qwen2.5-coder:14b` (~9 GB) — higher quality
- `nomic-embed-text` (~270 MB) — RAG embeddings

> **Qwen3-Coder / Qwen3-Coder-Next:** not in the official Ollama library at writing. If/when published, add to `config/models.yaml` and re-run `pull_models_local.sh`.

## 4. (Optional) Ubuntu worker setup

```bash
bash scripts/check_remote_worker.sh        # probe — no changes
bash scripts/install_remote_worker.sh      # interactive — prompts before any apt/install
bash scripts/pull_models_remote.sh         # pull baseline models on the worker
```

The install script does **not** touch your existing systemd Ollama config — it inspects first and asks before any change.

## 5. Build an index and test

```bash
python scripts/build_index.py --source . --config config/rag_config.yaml
python scripts/query_rag.py "What does the router do?"
```

## 6. Verify

```bash
bash scripts/health_check.sh
```

Expect green OKs for Ollama, indexes, Python venv, ripgrep.
