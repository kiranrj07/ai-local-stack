# 11 — Privacy Checklist

Run through this before sharing a result, enabling a network-backed tool, or onboarding new code.

## ✅ Local-only baseline

- [ ] `bash scripts/switch_mode.sh status` → mode is `local` (or `hybrid` and you intended that)
- [ ] No file in this repo contains an API key:
  ```bash
  rg -nE 'sk-|OPENAI_API_KEY|ANTHROPIC_API_KEY|GROQ_API_KEY|OPENROUTER_API_KEY' . 2>/dev/null
  ```
- [ ] Mac Ollama is bound to localhost only:
  ```bash
  lsof -nP -iTCP:11434 -sTCP:LISTEN
  # Expect:  ollama ... TCP 127.0.0.1:11434 (LISTEN)
  ```
- [ ] No proxy env vars are pointing outbound traffic somewhere unexpected:
  ```bash
  env | grep -iE 'HTTP_PROXY|HTTPS_PROXY|ALL_PROXY'
  ```
- [ ] MCP filesystem allowed root is the project only — `grep server-filesystem config/mcp_config.example.json`
- [ ] Phoenix data is in `~/.phoenix`, not exported anywhere
- [ ] Continue's `allowAnonymousTelemetry: false`
- [ ] Aider's `analytics: false`

## ⚠️ Cloud-risk checks (must all be FALSE)

- [ ] OpenAI / Anthropic / OpenRouter / Mistral / Groq keys in env or shell rc files
- [ ] Firecrawl Cloud configured (use self-hosted only)
- [ ] Langfuse Cloud configured (use self-hosted only)
- [ ] MCP servers `_disabled_github`, `_disabled_web_browser` enabled without need
- [ ] Any `requirements.txt` line that points to a cloud SDK you don't use

## Ubuntu worker checks (when in hybrid mode)

- [ ] Worker Ollama bind:
  ```bash
  ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP "ss -tln | grep 11434"
  ```
  - `127.0.0.1:11434` → ✅ private; SSH tunnel required (preferred)
  - `*:11434` or `0.0.0.0:11434` → ⚠️ LAN-exposed
  - `REPLACE_ME_WORKER_LAN_IP:11434` → ⚠️ LAN-exposed; firewall to Mac IP only

- [ ] If you must expose on LAN, restrict with ufw:
  ```bash
  ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP "sudo ufw allow from <MAC_IP> to any port 11434 && sudo ufw deny 11434"
  ```

- [ ] To switch Ubuntu Ollama to localhost only:
  ```bash
  ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP 'sudo systemctl edit ollama'   # add: [Service]\nEnvironment="OLLAMA_HOST=127.0.0.1"
  ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP 'sudo systemctl daemon-reload && sudo systemctl restart ollama'
  ```
  Then always use `start_remote_ollama_tunnel.sh` for hybrid mode.

## VS Code telemetry

- Settings → search "telemetry" → set `telemetry.telemetryLevel` to `off`.
- Continue extension: `allowAnonymousTelemetry: false` (set in example).

## Logs / traces storage

- `logs/` directory in this project. Review before sharing the project externally.
- `~/.phoenix` for Phoenix spans. Review or delete with `rm -rf ~/.phoenix` if you need a clean slate.

## Decision rule

If any of the **Cloud-risk checks** is true and you didn't explicitly enable it, **stop** and disable it before continuing.
