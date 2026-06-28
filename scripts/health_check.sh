#!/usr/bin/env bash
# End-to-end health check. Run with: bash scripts/health_check.sh
set -u
RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; RST=$'\e[0m'
ok()   { printf "  ${GRN}OK${RST}    %s\n" "$1"; }
warn() { printf "  ${YEL}WARN${RST}  %s\n" "$1"; }
miss() { printf "  ${RED}MISS${RST}  %s\n" "$1"; }

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$ROOT/config/system.yaml"
MODE=$(awk '/^mode:/{print $2; exit}' "$CFG")

echo "=== health_check.sh ==="
echo "active mode (from system.yaml): $MODE"
echo

echo "[mac ollama]"
if curl -fsS --max-time 4 http://localhost:11434/api/tags >/dev/null 2>&1; then ok "localhost:11434 reachable"
else miss "Mac Ollama not reachable on 11434"; fi
echo

if [ "$MODE" = "hybrid" ]; then
  echo "[remote worker]"
  USER=$(awk -F': *' '/^user:/{gsub(/"/,"",$2); print $2}' "$ROOT/config/remote_worker.yaml")
  IP=$(  awk -F': *' '/^ip:/  {gsub(/"/,"",$2); print $2}' "$ROOT/config/remote_worker.yaml")
  TARGET="${USER}@${IP}"
  if ssh -o ConnectTimeout=5 -o BatchMode=yes "$TARGET" true 2>/dev/null; then ok "ssh $TARGET"
  else miss "ssh $TARGET failed"; fi
  if curl -fsS --max-time 4 http://localhost:11435/api/tags >/dev/null 2>&1; then ok "tunnel localhost:11435 reachable"
  else warn "tunnel not up (run: bash scripts/start_remote_ollama_tunnel.sh)"; fi
  if ssh -o BatchMode=yes "$TARGET" "ollama list | awk 'NR>1{print \$1}' | grep -qx qwen2.5-coder:14b" 2>/dev/null; then
    ok "remote model qwen2.5-coder:14b present"
  else
    warn "remote model qwen2.5-coder:14b missing"
  fi
  echo
fi

echo "[indexes]"
for f in "indexes/faiss/vectors.faiss" "indexes/bm25/bm25.pkl" "indexes/metadata.sqlite3"; do
  [ -f "$ROOT/$f" ] && ok "$f" || miss "$f"
done
echo

echo "[python venv]"
if [ -d "$ROOT/.venv" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
  ok "venv active: $(python --version 2>&1)"
  for pkg in yaml faiss rank_bm25 sentence_transformers; do
    if python -c "import $pkg" 2>/dev/null; then ok "import $pkg"; else miss "import $pkg"; fi
  done
else
  miss "no .venv (run install_dependencies.sh)"
fi
echo

echo "[ripgrep]"
command -v rg >/dev/null 2>&1 && ok "rg present" || miss "rg not installed"
echo

echo "[phoenix]"
if curl -fsS --max-time 2 http://localhost:6006 >/dev/null 2>&1; then ok "phoenix UI reachable on :6006"
else warn "phoenix not running (optional)"; fi
echo
echo "Done."
