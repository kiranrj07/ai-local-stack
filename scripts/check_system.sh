#!/usr/bin/env bash
# Detect prerequisites on the Mac. Read-only — does not install anything.
# Run with: bash scripts/check_system.sh
set -u
RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; RST=$'\e[0m'
ok()   { printf "  ${GRN}OK${RST}    %s\n" "$1"; }
warn() { printf "  ${YEL}WARN${RST}  %s\n" "$1"; }
miss() { printf "  ${RED}MISS${RST}  %s\n" "$1"; }

echo "=== ai-local-stack: check_system.sh ==="
echo "cwd: $(pwd)"
echo

echo "[OS]"
uname -srm
sw_vers 2>/dev/null | sed 's/^/  /'
echo

echo "[CPU / Memory]"
echo "  cores : $(sysctl -n hw.ncpu 2>/dev/null)"
echo "  ram   : $(($(sysctl -n hw.memsize 2>/dev/null)/1024/1024/1024)) GB"
echo "  chip  : $(sysctl -n machdep.cpu.brand_string 2>/dev/null)"
echo

echo "[Tools]"
for t in git curl python3 pip3 node npm npx docker rg ollama; do
  if command -v "$t" >/dev/null 2>&1; then
    ok "$t -> $(command -v "$t")"
  else
    miss "$t not installed"
  fi
done
echo

echo "[Ollama]"
if command -v ollama >/dev/null 2>&1; then
  ollama --version 2>&1 | sed 's/^/  /'
  if lsof -nP -iTCP:11434 -sTCP:LISTEN 2>/dev/null | tail -n +2 | grep -q "127\.0\.0\.1:11434"; then
    ok "ollama listening on 127.0.0.1:11434 (private)"
  elif lsof -nP -iTCP:11434 -sTCP:LISTEN 2>/dev/null | tail -n +2 | grep -qE "\*:11434|0\.0\.0\.0:11434"; then
    warn "ollama listening on ALL interfaces. See docs/11-privacy-checklist.md"
  else
    warn "ollama port 11434 not listening — run: ollama serve &"
  fi
  echo "  models:"
  ollama list 2>/dev/null | sed 's/^/    /'
fi
echo

echo "[Python venv]"
[ -d ".venv" ] && ok ".venv present" || warn ".venv not present (run: bash scripts/install_dependencies.sh)"
echo

echo "[Indexes]"
[ -f "indexes/faiss/vectors.faiss" ] && ok "FAISS index present" || miss "FAISS index missing (run build_index.py)"
[ -f "indexes/bm25/bm25.pkl" ]        && ok "BM25 index present"  || miss "BM25 index missing"
[ -f "indexes/metadata.sqlite3" ]     && ok "metadata.sqlite3 present" || miss "metadata.sqlite3 missing"
echo
echo "Done."
