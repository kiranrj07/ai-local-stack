#!/usr/bin/env bash
# Idempotent remote worker setup. Inspects state, then prompts before installing.
# Does NOT silently reconfigure Ollama bind address.
# Run with: bash scripts/install_remote_worker.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$ROOT/config/remote_worker.yaml"
USER=$(awk -F': *' '/^user:/{gsub(/"/,"",$2); print $2}' "$CFG")
IP=$(  awk -F': *' '/^ip:/  {gsub(/"/,"",$2); print $2}' "$CFG")
TARGET="${USER}@${IP}"

echo "=== install_remote_worker.sh -> $TARGET ==="
echo "This script INSPECTS first, then prompts before installing anything."
echo

bash "$ROOT/scripts/check_remote_worker.sh" || { echo "remote checks failed." >&2; exit 1; }

read -r -p $'\nProceed with installation steps? (only missing pieces) [y/N]: ' yn
case "$yn" in [yY]*) ;; *) echo "aborted."; exit 0;; esac

# 1) APT basics
ssh -o BatchMode=no "$TARGET" 'bash -se' <<'REMOTE'
set -euo pipefail
need=()
for p in curl ca-certificates ripgrep; do
  dpkg -s "$p" >/dev/null 2>&1 || need+=("$p")
done
if [ "${#need[@]}" -gt 0 ]; then
  echo "[remote] installing: ${need[*]}"
  sudo apt-get update -y
  sudo apt-get install -y "${need[@]}"
else
  echo "[remote] base packages OK"
fi
REMOTE

# 2) Ollama
ssh -o BatchMode=no "$TARGET" 'bash -se' <<'REMOTE'
set -euo pipefail
if command -v ollama >/dev/null 2>&1; then
  echo "[remote] ollama already installed: $(ollama --version)"
else
  echo "[remote] installing ollama via official script"
  curl -fsSL https://ollama.com/install.sh | sh
fi
sudo systemctl enable --now ollama || true
systemctl is-active ollama || true
REMOTE

# 3) Models
ssh -o BatchMode=yes "$TARGET" 'bash -se' <<'REMOTE'
set -euo pipefail
for m in qwen2.5-coder:14b nomic-embed-text; do
  if ollama list | awk 'NR>1{print $1}' | grep -qx "$m"; then
    echo "[remote] $m already present"
  else
    echo "[remote] pulling $m"
    ollama pull "$m" || echo "[remote] WARN: failed to pull $m"
  fi
done
REMOTE

echo
echo "Done. Next: bash scripts/check_remote_worker.sh"
echo "Then start tunnel: bash scripts/start_remote_ollama_tunnel.sh"
