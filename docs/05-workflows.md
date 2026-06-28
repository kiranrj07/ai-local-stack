# 05 — Workflows

Common end-to-end recipes.

## 1. Ask a question about this codebase

```bash
source .venv/bin/activate
python scripts/build_index.py --rebuild        # only if you haven't built yet
python scripts/query_rag.py "How does fallback to local mode work?"
```

## 2. Debug a runtime error using logs

Capture the error, then:
```bash
python scripts/hybrid_search.py --rg "exact error string"
python scripts/query_rag.py "What handles ${SymbolFromTrace} and where could ${error} originate?"
```

## 3. Add a feature with Cline

1. Open VS Code in `~/ai-local-stack`.
2. Install the Cline extension.
3. Set provider = `Ollama`, base URL = `http://localhost:11434`, model = `qwen2.5-coder:14b`.
4. Open Cline → type the feature request → review every file change before Approve.

For hybrid mode, point Cline to `http://localhost:11435` after `start_remote_ollama_tunnel.sh`.

## 4. Refactor safely with Aider

```bash
brew install aider                         # or pipx install aider-chat
cd ~/some-other-repo
aider --config ~/ai-local-stack/config/aider_config.local.example.yaml
# Inside aider: review the proposed diff before /yes
```

## 5. Generate docs from a repo

```bash
python scripts/build_index.py --source ~/some-other-repo --rebuild
python scripts/query_rag.py "Produce a markdown developer guide covering setup, configuration, and key modules. Include file paths and line ranges."
```

## 6. Ingest external docs

Drop PDFs/HTML into `data/raw/`, then:
```bash
pip install docling                       # or unstructured
python scripts/ingest_docs.py --input data/raw --output data/processed
# Now point rag_config.yaml at data/processed and rebuild
python scripts/build_index.py --source data/processed --rebuild
```

## 7. Rebuild the RAG index after edits

```bash
python scripts/build_index.py --rebuild
```

## 8. Run an evaluation (manual smoke)

```bash
python tests/test_rag_query.py
python tests/test_embedding.py
python tests/test_faiss_load.py
```
Ragas/DeepEval are commented out in `requirements.txt` — uncomment if you want them. Both will use the local Ollama model as judge.

## 9. Privacy audit before enabling an external tool

Walk through `docs/11-privacy-checklist.md` end-to-end. If anything fails, **do not** enable the cloud-backed integration.
