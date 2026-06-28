# 09 — Observability

## Phoenix (local)

[Arize Phoenix](https://github.com/Arize-ai/phoenix) is a local trace/eval UI. It stores everything on disk in `~/.phoenix`. No cloud account, no telemetry, no auth — bind it to localhost only.

Start:
```bash
bash scripts/start_phoenix.sh           # opens http://localhost:6006
```

Instrumenting `query_rag.py`:
```python
from phoenix.otel import register
register(project_name="ai-local-stack")
```
Add that at the top of `query_rag.py` and Phoenix will collect spans for each LLM/embedding call.

What to trace:
- **Embedding latency** — spikes here usually mean the embedding model isn't loaded into VRAM yet.
- **Retrieval recall** — log the hit `rel_path:line` list per query; you'll spot bad chunking quickly.
- **Generation tokens/sec** — drops mean a context-size or memory issue.

## Langfuse (self-host only)

**Do not** point at `cloud.langfuse.com`. If you want Langfuse, run it locally with Docker:
```
git clone https://github.com/langfuse/langfuse
cd langfuse && docker compose up -d
```
Then set `LANGFUSE_HOST=http://localhost:3000` and the public/secret keys printed at first login. Never put cloud keys in this repo.

## Debugging bad RAG results

1. Re-run with `--no-llm` to inspect retrieved hits only:
   ```bash
   python scripts/query_rag.py "your question" --no-llm
   ```
2. Try the same query through `hybrid_search.py` and through `hybrid_search.py --rg` (ripgrep). If only one of the three returns relevant results, your chunking / embedding / weighting is off.
3. Lower `chunk_size` for fine-grained code questions; raise it for high-level "what does this module do?" questions.
4. Enable the reranker — it's the single biggest precision lever.
