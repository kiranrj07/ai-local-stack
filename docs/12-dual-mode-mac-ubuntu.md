# 12 — Dual Mode (Mac + Ubuntu Worker)

## Roles

| Role | Mac (controller) | Ubuntu worker |
| --- | --- | --- |
| IDE / agents | yes | no |
| RAG orchestration | yes (always) | no |
| FAISS / BM25 / SQLite | yes (always) | no |
| Ollama (LLM serving) | local mode only | hybrid mode |
| Reranker | yes | no |
| Phoenix | yes | no |

Indexes always live on the Mac. Only inference moves between machines.

## Topology

- **Static IP:** REPLACE_ME_WORKER_LAN_IP
- **SSH alias:** `sshj` (defined in `~/.zshrc` line 120: `alias sshj='ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP'`)
- **Remote user:** REPLACE_ME_USER
- **Remote OS:** Ubuntu 24.04 LTS, kernel 6.17, x86_64, 20 cores, 15 GB RAM, NVIDIA RTX 4050 (6 GB VRAM, driver 595.71.05, CUDA 13.2)

## Two connection options

### Option A — SSH tunnel (RECOMMENDED — private)

Mac connects through a forwarded localhost port. Ollama on Ubuntu can stay on `127.0.0.1` (no LAN exposure required).

```bash
bash scripts/start_remote_ollama_tunnel.sh
# Mac:11435  ->  Ubuntu:11434
```

`config/system.yaml` in hybrid block:
```yaml
hybrid:
  ollama_url: "http://localhost:11435"
  connection_type: "ssh_tunnel"
  ssh_tunnel_command: "ssh -N -L 11435:localhost:11434 REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP"
```

Test:
```bash
curl http://localhost:11435/api/tags
```

### Option B — Direct LAN (LESS SAFE)

Ollama on Ubuntu binds to its LAN IP. Anyone on your subnet can hit it unless you firewall.

To enable on the worker:
```bash
ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP 'sudo systemctl edit ollama'
# Add:
#   [Service]
#   Environment="OLLAMA_HOST=0.0.0.0"
ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP 'sudo systemctl daemon-reload && sudo systemctl restart ollama'
```

Then **firewall** to allow only the Mac:
```bash
MAC_IP=$(ipconfig getifaddr en0)
ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP "sudo ufw allow from $MAC_IP to any port 11434 && sudo ufw deny 11434 && sudo ufw enable"
```

`config/system.yaml`:
```yaml
hybrid:
  ollama_url: "http://REPLACE_ME_WORKER_LAN_IP:11434"
  connection_type: "direct_lan"
  direct_lan_url: "http://REPLACE_ME_WORKER_LAN_IP:11434"
```

Test:
```bash
curl http://REPLACE_ME_WORKER_LAN_IP:11434/api/tags
```

**Choose Option A unless you have a specific reason not to.** The tunnel has near-zero overhead and removes one whole class of exposure.

## Current worker state (at setup time)

Ollama on the Ubuntu worker is currently bound to `*:11434` (LAN-exposed). To harden:
```bash
ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP 'sudo systemctl edit ollama'
# Add:
#   [Service]
#   Environment="OLLAMA_HOST=127.0.0.1"
ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP 'sudo systemctl daemon-reload && sudo systemctl restart ollama'
```
Then use the SSH tunnel from the Mac for hybrid mode.

## Switching modes

```bash
bash scripts/switch_mode.sh local      # everything on Mac
bash scripts/switch_mode.sh hybrid     # inference → Ubuntu
bash scripts/switch_mode.sh status     # print current
```

`switch_mode.sh hybrid` does not auto-start the tunnel — run `start_remote_ollama_tunnel.sh` first. The router will print a clear warning if it falls back to local because the hybrid endpoint isn't reachable.

## Validating remote Ollama

```bash
bash scripts/check_remote_worker.sh        # static probe (no inference)
curl http://localhost:11435/api/tags       # via tunnel
ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP ollama list        # raw list
```

## Pulling models remotely

```bash
bash scripts/pull_models_remote.sh
# or interactively:
ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP ollama pull qwen2.5-coder:14b
```

## Fallback

In hybrid mode, `core.router.resolve_endpoint()` pings the remote endpoint. If unreachable and `fallback.enabled: true` (default), it returns the local endpoint and sets `fell_back=True`. Scripts print a clear `FALLBACK` line on stderr.

To disable fallback (fail-loud):
```yaml
fallback:
  enabled: false
```

## Troubleshooting

### `sshj` not working from scripts
The alias is shell-level. Scripts use the explicit form: `ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP`. Verify with `bash scripts/check_remote_worker.sh`.

### Ubuntu unreachable
```bash
ping REPLACE_ME_WORKER_LAN_IP
ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP true
# If neither works: check Wi-Fi/Ethernet, the worker may have rotated to a different IP.
```

### Ollama not running on Ubuntu
```bash
ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP 'systemctl status ollama'
ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP 'sudo systemctl restart ollama'
```

### Port 11434 not reachable on Ubuntu
- From Mac: blocked at firewall — see ufw section above.
- From worker itself: Ollama may have crashed; check journalctl: `ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP 'journalctl -u ollama -n 50'`.

### SSH tunnel port busy on Mac
```bash
lsof -nP -iTCP:11435 -sTCP:LISTEN
# kill the orphan ssh, or change LOCAL_PORT in start_remote_ollama_tunnel.sh
```

### Model missing on remote
```bash
bash scripts/pull_models_remote.sh
```

### Slow responses
- First request loads model into VRAM. RTX 4050 has 6 GB, so a 14B model partially spills to CPU — switch to `qwen2.5-coder:7b` if responsiveness matters.
- Confirm GPU is actually being used: `ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP 'nvidia-smi'` during a request.

### Firewall blocks access
```bash
ssh REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP 'sudo ufw status verbose'
```
