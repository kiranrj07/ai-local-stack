# 08 — MCP Security

## What MCP is

Model Context Protocol — a standard for letting LLM agents call tools (filesystem, git, web, etc.) via a JSON-RPC server. Powerful because the agent can read/write your machine. Risky for the same reason.

## Filesystem server

The example config `config/mcp_config.example.json` restricts the filesystem server to exactly one root:
```
"args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/krajp/ai-local-stack"]
```

**Do not add `$HOME` or `/` to this list.** Your home directory holds `.aws`, `.azure`, `.kube`, `.ssh`, `.gcp` — handing those to an agent is a credential leak waiting to happen.

To add another safe path:
```jsonc
"args": [
  "-y", "@modelcontextprotocol/server-filesystem",
  "/Users/krajp/ai-local-stack",
  "/Users/krajp/code/some-project"
]
```

## Git server

Scoped to a single repo:
```
"args": ["-y", "@modelcontextprotocol/server-git", "--repository", "/Users/krajp/ai-local-stack"]
```

Destructive commands (`reset --hard`, `push --force`, `branch -D`) work but the agent must call them explicitly. Review every git tool call. Consider disabling the git server entirely when the agent doesn't need it.

## Docker server

Optional. Disabled in the example. If enabled, the agent can `docker exec` into any running container and `docker run` arbitrary images. Only turn this on if:
- You actively need it
- No production containers are running on the same Docker daemon
- You've reviewed which images/volumes are exposed

## Network-required servers (DISABLED by default)

| Server | Network reaches | Risk |
| --- | --- | --- |
| `_disabled_github` | api.github.com | Code/comments leak to GitHub, requires PAT |
| `_disabled_web_browser` (puppeteer) | Arbitrary URLs | Visits any site the model asks for |
| Future search server | Search engine | Query strings leak |

All are prefixed `_disabled_` in the example so they won't load. Remove the prefix to enable, and only after you understand the data path.

## Recommended pattern

1. Start with **filesystem + git** only, scoped to one repo.
2. Watch the agent's tool-call log for a session before adding more.
3. If you enable Docker, **also** add a non-MCP guardrail (separate Docker context).
4. Treat any network-required MCP server as a privacy boundary crossing — `docs/11-privacy-checklist.md` covers the audit steps.
