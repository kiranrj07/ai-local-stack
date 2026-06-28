# 07 — Agent Guide

Three agents are supported. All run against your local or remote Ollama — no cloud accounts.

## Cline (VS Code extension)

- Install: VS Code Extensions → search "Cline" (saoudrizwan.claude-dev).
- **Provider:** Ollama
- **Base URL — local:** `http://localhost:11434`
- **Base URL — hybrid:** `http://localhost:11435` (start the tunnel first)
- **Model:** `qwen2.5-coder:14b`

Auto-approve OFF until you've audited Cline's command list. Open VS Code only on `~/ai-local-stack` (or another single project) so Cline's file access is naturally scoped.

See `config/cline_local_notes.md` and `config/cline_hybrid_notes.md`.

## Aider

- Install: `brew install aider` or `pipx install aider-chat`.
- Local: `aider --config config/aider_config.local.example.yaml`
- Hybrid: `aider --config config/aider_config.hybrid.example.yaml`

Aider reads OpenAI-compatible APIs; Ollama exposes one at `/v1`. Don't set `OPENAI_API_KEY` in your shell unless you also intend to call OpenAI — aider routes by model name and an env-var key will get used if present.

Safe workflow:
- `auto-commits: false` (set in the example configs) — you review every diff
- Stage with `git add -p` before letting aider proceed
- Use `/diff` inside aider before `/yes`

## Continue (VS Code extension)

- Install: VS Code Extensions → "Continue".
- Copy `config/continue_config.local.example.json` to `~/.continue/config.json` (back up your existing one first).
- For hybrid: use `continue_config.hybrid.example.json` and start the tunnel.

Continue supports chat + tab autocomplete + embeddings. Set `allowAnonymousTelemetry: false` (already set in the example).

## Qwen Code (optional)

Qwen Code is Alibaba's CLI agent. It supports OpenAI-compatible endpoints, so the same `http://localhost:11434/v1` (or `:11435` for hybrid) works. Install per their docs — keep it pointed at local-only by setting `OPENAI_API_BASE` to your local endpoint and leaving `OPENAI_API_KEY` as a dummy string.

## Recommended prompts

For code review:
> "Review the diff in the current chunk for correctness bugs, dead code, and missing tests. Cite line numbers."

For a new feature:
> "I want to add X. Read the relevant files, propose a plan with file changes and a test, then wait for my approval before editing."

For debugging:
> "Here is the error. Find the most likely failure mode, list 2-3 hypotheses, and propose minimal repro steps."

## Safety best practices

1. Pin one model — don't auto-pick "latest" if it changed under you.
2. Disable auto-commit / auto-approve until you've watched the agent for a while.
3. Keep MCP filesystem scoped to one project root.
4. Don't paste secrets into the chat box.
