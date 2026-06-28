# 03 — User Manual

## Day-to-day flow

1. Activate the venv once per shell:
   ```bash
   cd ~/ai-local-stack && source .venv/bin/activate
   ```
2. Make sure Ollama is up (Mac or Ubuntu, depending on mode):
   ```bash
   bash scripts/health_check.sh
   ```
3. Ask questions about your repo:
   ```bash
   python scripts/query_rag.py "Where do we configure ssh?"
   ```
4. Exact-match search when you know the string:
   ```bash
   python scripts/hybrid_search.py --rg "OLLAMA_HOST"
   ```

## How to ask repo questions

`query_rag.py` always:
- runs hybrid retrieval (FAISS top 8 + BM25 top 8 → final top 5)
- builds a prompt that includes source headers and code blocks
- calls Ollama and prints the answer with `[path:start-end]` citations
- echoes which mode and model were actually used (helpful when fallback fires)

If the answer says **"I don't know from the indexed sources,"** the question is asking about something not in the index — either rebuild against a different source dir or use ripgrep.

## How to rebuild indexes

After you change source code or `config/rag_config.yaml`:
```bash
python scripts/build_index.py --rebuild
```

To point at a different repo:
```bash
python scripts/build_index.py --source ~/some-other-repo --rebuild
```
Or edit `config/rag_config.yaml`'s `source.dir`.

## How to update models

Local:
```bash
ollama pull qwen2.5-coder:14b
```
Remote:
```bash
ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP ollama pull qwen2.5-coder:14b
# or: bash scripts/pull_models_remote.sh
```

## How to switch modes

```bash
bash scripts/switch_mode.sh status      # show current mode + reachable endpoint
bash scripts/switch_mode.sh hybrid      # flip to hybrid (needs tunnel up)
bash scripts/switch_mode.sh local       # back to Mac-only
```

## How to debug issues

1. `bash scripts/health_check.sh` — covers 90 % of issues.
2. Tail `logs/rag.log` and `logs/ssh_tunnel.log`.
3. Hit the Ollama endpoint directly:
   ```bash
   curl -fsS http://localhost:11434/api/tags
   curl -fsS http://localhost:11435/api/tags   # tunneled hybrid
   ```
4. Check the router:
   ```bash
   python core/router.py status
   ```
