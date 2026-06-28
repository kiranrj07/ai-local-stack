#!/usr/bin/env bash
# Pull baseline models on the Ubuntu worker.
# Run with: bash scripts/pull_models_remote.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$ROOT/config/remote_worker.yaml"
USER=$(awk -F': *' '/^user:/{gsub(/"/,"",$2); print $2}' "$CFG")
IP=$(  awk -F': *' '/^ip:/  {gsub(/"/,"",$2); print $2}' "$CFG")
TARGET="${USER}@${IP}"

MODELS=("qwen2.5-coder:14b" "nomic-embed-text")
for m in "${MODELS[@]}"; do
  echo "[remote] checking $m"
  if ssh -o BatchMode=yes "$TARGET" "ollama list | awk 'NR>1{print \$1}' | grep -qx '$m'"; then
    echo "  already present"
  else
    echo "  pulling..."
    ssh -o BatchMode=yes "$TARGET" "ollama pull $m"
  fi
done
echo "done."
