# 13 — VS Code, Modes, and Agents (FAQ-style)

## Q: I'll be using VS Code. Can I run `query_rag.py` AND use Cline at the same time?

**Yes — they're independent and complementary.**

| Tool | Where it runs | What it does | Touches code? |
|---|---|---|---|
| `query_rag.py` | VS Code's integrated terminal (or any terminal) | Read-only Q&A over your indexed repo | No — read only |
| Cline | VS Code panel | Agentic edit-run-test loop with MCP tools | Yes — writes files |
| Continue | VS Code panel | Chat + tab autocomplete | Suggestions only |
| Aider | Terminal | Git-aware refactor agent | Proposes diffs you approve |

You can have all four running. They all hit the same Ollama on `:11434` (or the auto-routed `:11435` in hybrid mode). Ollama queues requests, so they don't fight for the model.

### Typical flow

1. **Open VS Code** on `/Users/krajp/ai-local-stack`.
2. Press `` ` `` (backtick) to open the integrated terminal.
3. In the terminal:
   ```bash
   cd ~/ai-local-stack && source .venv/bin/activate
   python scripts/query_rag.py "Where do we configure the SSH tunnel?"
   ```
4. While that's still on screen, open Cline's panel (left sidebar) and ask:
   > "Following on from the query — add a unit test that asserts auto mode falls back to local when the tunnel is closed."
5. Cline reads files (using MCP filesystem scoped to the project), edits a test file, and asks for approval before running.

### What query_rag.py does NOT have

- **No filesystem write access.** It only reads the FAISS+BM25 indexes built earlier.
- **No MCP tools.** It does not call Cline's filesystem/git/docker MCP servers.
- **No tab completion.** That's Continue's job.
- **No diff or commit.** That's Aider's job.

Think of it as: `query_rag.py` is a fast, dumb librarian. Cline is a slow, smart coder.

---

## Q: I find the "switch to hybrid manually" workflow confusing. Can it just figure out?

**Yes — that's `mode: auto` (now the default).**

`config/system.yaml` ships with:
```yaml
mode: auto
```

How auto works (in order, per call):
1. Is `hybrid.ollama_url` (the tunnel port, `localhost:11435`) reachable? → use hybrid.
2. If not and `connection_type: ssh_tunnel`, try to open the tunnel automatically via `ssh -f -N -L 11435:localhost:11434 REPLACE_ME_USER@REPLACE_ME_WORKER_LAN_IP`. Re-probe.
3. Still not reachable? → silently use local Mac Ollama.

This means:
- When your worker is **on the same Wi-Fi and key auth works**, every query routes to the worker.
- When you're **away from home / worker is off / SSH is blocked**, queries route to the Mac. No error, no manual switch.

You can still force a mode when you want to:
```bash
bash scripts/switch_mode.sh local      # never try the worker
bash scripts/switch_mode.sh hybrid     # require the worker (falls back per fallback config)
bash scripts/switch_mode.sh auto       # the default
bash scripts/switch_mode.sh status     # show what auto resolved to right now
```

### When auto picks "hybrid", what about VS Code agents?

VS Code agents (Cline, Continue) read **their own** `apiBase` setting — they don't ask the Python router. To keep them in sync with auto, set them to the tunnel URL (`http://localhost:11435`) and run:
```bash
bash scripts/start_remote_ollama_tunnel.sh
```
once at the start of your session. The tunnel is idempotent; if it's already up, the script no-ops.

If you don't want to think about it for the IDE either, point Cline/Continue at **`http://localhost:11434`** (Mac Ollama). They'll always work, just on the Mac. Use `query_rag.py` for the worker-backed RAG when you specifically want the worker.

### Testing auto

```bash
bash scripts/switch_mode.sh status
# requested mode : auto
# active mode    : hybrid
# reason         : auto -> hybrid via http://localhost:11435

# Disconnect from Wi-Fi or kill the tunnel, then:
bash scripts/switch_mode.sh status
# requested mode : auto
# active mode    : local (fell back)
# reason         : auto: hybrid endpoint http://localhost:11435 unreachable; using local
```
