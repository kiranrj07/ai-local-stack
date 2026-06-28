# 14 — Cline + Continue setup (click-by-click)

This doc covers the **one-time** UI steps. Continue's config file is already
written by the setup script; Cline only has a UI, so you'll click through it.

## 1. Install the extensions

In VS Code: `Cmd+Shift+X` → search → Install:
- **Cline**  (publisher: saoudrizwan, ID `saoudrizwan.claude-dev`)
- **Continue**  (publisher: Continue, ID `Continue.continue`)

Restart VS Code.

## 2. Continue — already configured

Your `~/.continue/config.yaml` has been replaced with a Mac+Ubuntu model list.
Your previous config is at `~/.continue/config.yaml.bak`.

Verify:
1. Open the Continue panel (left sidebar, the Continue icon).
2. Click the model name at the top of the panel → you should see:
   - `Qwen2.5 Coder 14B (Mac, local)`
   - `Qwen2.5 Coder 7B (Mac, fast)`
   - `Qwen2.5 Coder 14B (Ubuntu, via SSH tunnel)`
3. Pick one. Type a question. If it answers, you're done.

If the Ubuntu profile is selected and you see a connection error, run
`aitool tunnel` in any terminal — Continue will retry on the next message.

## 3. Cline — one-time UI setup

Cline keeps its provider/model in VS Code's extension storage. Walk through this once.

### Open Cline settings
1. Click the Cline icon in the left sidebar.
2. Click the gear icon at the top of the Cline panel → **API Configuration**.

### Set provider
- **API Provider:** `Ollama`
- **Ollama Base URL:** pick one:
  - `http://localhost:11434`  ← Mac Ollama. Always works.
  - `http://localhost:11435`  ← Ubuntu via SSH tunnel. Run `aitool tunnel` first.
- **Model ID:** type `qwen2.5-coder:14b` (or `:7b` for faster).

Click **Done** / **Save**.

### Safety settings (recommended)
In the same settings panel:
- **Auto-approve actions:** leave OFF until you trust Cline on this repo.
- **Allowed commands list:** start empty. Cline will ask before every shell command.

### MCP (Model Context Protocol) — optional
Cline → ☰ → **MCP Servers** → Edit `cline_mcp_settings.json`. Paste from
`/Users/krajp/ai-local-stack/config/mcp_config.example.json`. Adjust the
filesystem root to the repo you're working on, e.g.:
```jsonc
"args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/krajp/code/myrepo"]
```

**Never** add `$HOME` or `/` to the filesystem args.

## 4. End-to-end check

```bash
# Make sure Ollama can answer
curl -s http://localhost:11434/api/tags | head
# Or via tunnel
aitool tunnel
curl -s http://localhost:11435/api/tags | head
```

Open VS Code on your project, open Cline panel, give it a small task:
> "Read README.md and summarize what this project does in 5 bullets."

If Cline replies and offers to read files, the wiring is good. Approve each
tool call as it appears.

## 5. Working on a cloned repo end-to-end

```bash
# Clone + auto-index
aitool clone https://github.com/owner/repo
# Open VS Code on the cloned dir (also opens the tunnel)
aitool open ~/code/repo
```

Inside VS Code:
1. Open Cline panel.
2. Confirm the API provider is Ollama and the model is `qwen2.5-coder:14b`.
3. Type a task. Recommended first prompt:
   > "Read the README and 3-5 entry-point files. Summarize the architecture and propose a step-by-step plan to add feature X. Do not edit files yet — wait for my approval on the plan."
4. Review the plan.
5. Approve file edits and shell commands one at a time.
6. When the change is good: approve `git checkout -b <feature-branch>`, then
   `git add` and `git commit`. Review the diff before `git push`.

## What Cline can do vs. what it can't

| Capability                              | Cline + qwen2.5-coder:14b |
| --- | --- |
| Read files in the open workspace        | ✅ (with approval) |
| Edit/create files                       | ✅ (you approve each diff) |
| Run shell commands (build, test, lint)  | ✅ (you approve each command) |
| Use MCP filesystem/git/Docker servers   | ✅ (you configure) |
| Multi-step planning                     | ✅ but **review every step** — local 14B drifts in long unattended loops |
| Cross-file refactor on large repos      | partial — model context is 32K tokens, won't fit everything |
| Iterate until tests pass autonomously   | works, but approve_all is OFF: you click each test run |
| Open a PR                               | yes via `gh pr create`, with approval |

## Troubleshooting

### "Cannot connect to API"
- For local: `curl http://localhost:11434/api/tags` — if empty, run `aitool pull-local` and make sure Ollama is running.
- For tunnel: `curl http://localhost:11435/api/tags` — if empty, `aitool tunnel`.

### Cline replies very slowly
First request loads the model into RAM/VRAM. Subsequent requests are fast. Switch to `qwen2.5-coder:7b` if responsiveness matters more than quality.

### Cline keeps re-reading the same file
Model is over its context limit. Either narrow the task, exclude irrelevant folders via `.gitignore`-style files, or split the task.

### Continue and Cline both running — resource conflict?
Both hit the same Ollama. Ollama queues requests, so it's fine, just slightly slower. If you want them on different models, set Continue to `qwen2.5-coder:7b` and Cline to `:14b`.
