# Cline — LOCAL profile

Cline is a VS Code extension. Install: VS Code → Extensions → search "Cline" (saoudrizwan.claude-dev).

## Provider settings (Cline → ⚙ → API Configuration)
- **API Provider:** `Ollama`
- **Base URL:** `http://localhost:11434`
- **Model ID:** `qwen2.5-coder:14b` (or `qwen2.5-coder:7b` for faster responses)

## Permissions
- Auto-approve: keep **off** while you trust-test Cline.
- Allowed working directory: open VS Code on `/Users/krajp/ai-local-stack` only.
- Avoid auto-running commands until you've reviewed Cline's command list.

## MCP
- Cline has its own MCP UI: Cline → ☰ → MCP Servers.
- Use `config/mcp_config.example.json` as a reference. Restrict filesystem to project root.

## Anti-cloud
- Do **not** select `Anthropic` / `OpenRouter` / `OpenAI` as the API provider.
- Do not enter any cloud API key — Cline will not call cloud APIs without one.

## Test prompt
> "List the Python files under scripts/ and summarize what each one does."
