# Cline — HYBRID profile

Inference runs on the Ubuntu worker. Start the tunnel first:
```
bash scripts/start_remote_ollama_tunnel.sh
```

## Provider settings
- **API Provider:** `Ollama`
- **Base URL:** `http://localhost:11435`  ← tunnel port, not 11434
- **Model ID:** `qwen2.5-coder:14b`

## Direct LAN alternative (less safe)
- Base URL: `http://REPLACE_ME_WORKER_LAN_IP:11434`
- Only use if Ubuntu Ollama is firewalled to the Mac IP only.
- See `docs/12-dual-mode-mac-ubuntu.md` for the hardening steps.

## Failure modes
- `connection refused on 11435` → tunnel isn't running, restart `start_remote_ollama_tunnel.sh`.
- Slow first token → model is being loaded into VRAM on Ubuntu; normal for first request.
