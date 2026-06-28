# 10 — Troubleshooting

## Ollama

### "ollama not responding on 11434"
```bash
ollama serve &                          # in another terminal
# or just open the Ollama macOS app
curl -fsS http://localhost:11434/api/tags    # verify
```

### "model not found"
```bash
ollama pull qwen2.5-coder:14b
```
or `bash scripts/pull_models_local.sh`.

### Slow first response
First request loads the model into RAM/VRAM. Subsequent requests are fast. Keep the model resident by sending a 1-token warmup at startup:
```bash
curl -s http://localhost:11434/api/generate -d '{"model":"qwen2.5-coder:14b","prompt":"hi","stream":false,"options":{"num_predict":1}}'
```

### Out of memory
On Mac with 24 GB, running 14B + IDE + browser is tight. Switch to `qwen2.5-coder:7b` for daily use:
- `models:` in `config/system.yaml` → `qwen2.5-coder:7b`
- Restart Ollama to free the 14B from memory.

## FAISS / index

### `ImportError: faiss-cpu`
You're on Python 3.13+. faiss-cpu doesn't ship arm64 wheels for 3.13+ yet. Drop to 3.11:
```bash
pyenv install 3.11.9
bash scripts/install_dependencies.sh
```

### "embedding model download error"
HF mirror or network issue. Try:
```bash
HF_HUB_OFFLINE=0 python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-base-en-v1.5')"
```
Or stay on `nomic-embed-text` via Ollama (no HF download).

### "bad retrieval" / "no results found"
- Did you rebuild after changing `source.dir`?  `python scripts/build_index.py --rebuild`
- Is the file extension in `include_extensions`? Check `config/rag_config.yaml`.
- Try `hybrid_search.py --rg "string"` to confirm the file is actually in the source dir.

## Agents

### Cline not reading files
- Confirm VS Code is opened on the project root, not `$HOME`.
- Cline → MCP Servers → check filesystem server is listed and the project root is allowed.

### Aider cannot connect to Ollama
- Local: `curl http://localhost:11434/api/tags` — if that fails, fix Ollama first.
- Hybrid: `curl http://localhost:11435/api/tags` — if that fails, restart the tunnel.
- Check `OPENAI_API_KEY` is unset in your shell (Aider auto-routes to OpenAI if it sees a key).

### Continue not using local model
- `~/.continue/config.json` — confirm `provider: "ollama"` and `apiBase: "http://localhost:11434"`.
- Look at Continue's output panel in VS Code; it logs every request URL.

## MCP

### MCP permission errors
- The filesystem server only allows paths inside the configured root. Check the `args:` array.
- If Cline shows "access denied", that's the filesystem server doing its job — don't widen the root, move the file into the project instead.

## Headroom

### Bad compressed output
- Disable compression for that query: `retrieval.compression.enabled: false`.
- Lower `min_chars_to_compress` only if your typical context is >10k chars.

## SSH / hybrid

### `ssh sshj` not working
- The alias is in `~/.zshrc` line 120. Verify with `type sshj` in an interactive zsh.
- If it works interactively but not in scripts, the script likely uses `bash` — call as `ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP` explicitly.

### "tunnel started but /api/tags not reachable"
- Wait 3 seconds and curl again — model API doesn't always come up the same instant the tunnel does.
- Check `logs/ssh_tunnel.log`.
- `lsof -nP -iTCP:11435 -sTCP:LISTEN` — if nothing is listening, the tunnel died.

### Port 11435 busy
```bash
lsof -nP -iTCP:11435 -sTCP:LISTEN
# kill the old tunnel if appropriate, then re-run start_remote_ollama_tunnel.sh
```

### "model missing on remote"
```bash
bash scripts/pull_models_remote.sh
```
or `ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP ollama pull qwen2.5-coder:14b`.

### Slow responses in hybrid mode
- First request loads the model into the RTX 4050's 6 GB VRAM. 14B + 16k context won't fully fit; some layers will spill to CPU. Use `qwen2.5-coder:7b` for snappier responses.
- Check `ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP nvidia-smi` while a request is in flight.
