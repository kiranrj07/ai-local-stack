#!/usr/bin/env bash
# Pull baseline models into the Mac's local Ollama.
# Run with: bash scripts/pull_models_local.sh
set -euo pipefail

if ! command -v ollama >/dev/null 2>&1; then
  echo "ollama not installed. brew install ollama" >&2; exit 1
fi
if ! curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "ollama not responding on 11434. Start it: 'ollama serve &' (or open the Ollama app)" >&2; exit 2
fi

MODELS=("qwen2.5-coder:7b" "qwen2.5-coder:14b" "nomic-embed-text")
for m in "${MODELS[@]}"; do
  if ollama list | awk 'NR>1{print $1}' | grep -qx "$m"; then
    echo "[local] $m already present"
  else
    echo "[local] pulling $m"
    ollama pull "$m"
  fi
done
echo "done. verify: ollama list"
