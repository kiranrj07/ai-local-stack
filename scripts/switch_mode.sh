#!/usr/bin/env bash
# Switch between auto, local, and hybrid modes, or print status.
# Edits config/system.yaml in-place. Run with:
#   bash scripts/switch_mode.sh {auto|local|hybrid|status}
#
# auto    : probe worker first, fall back to Mac if unreachable (RECOMMENDED)
# local   : force Mac Ollama
# hybrid  : force worker; fall back per fallback.enabled
# status  : print current resolved endpoint
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$ROOT/config/system.yaml"
[ -f "$CFG" ] || { echo "ERROR: $CFG not found" >&2; exit 2; }

cmd="${1:-status}"

set_mode() {
  local new="$1"
  case "$new" in auto|local|hybrid) ;; *) echo "mode must be 'auto', 'local', or 'hybrid'"; exit 2;; esac
  awk -v new="$new" '
    BEGIN { done=0 }
    /^mode:/ && !done { sub(/mode:.*/, "mode: " new); done=1 }
    { print }
  ' "$CFG" > "$CFG.tmp" && cat "$CFG.tmp" > "$CFG" && rm -f "$CFG.tmp"
  echo "set mode=$new in $CFG"
}

status() {
  if [ -d "$ROOT/.venv" ]; then
    # shellcheck disable=SC1091
    source "$ROOT/.venv/bin/activate"
  fi
  if ! python -c "import yaml" 2>/dev/null; then
    echo "WARN: pyyaml not installed yet — printing raw file head." >&2
    head -3 "$CFG"
    return 0
  fi
  python "$ROOT/core/router.py" status
}

case "$cmd" in
  auto|local|hybrid) set_mode "$cmd"; echo; status ;;
  status)            status ;;
  -v|--verbose)
    if [ -d "$ROOT/.venv" ]; then
      # shellcheck disable=SC1091
      source "$ROOT/.venv/bin/activate"
    fi
    python "$ROOT/core/router.py" status --verbose
    ;;
  *) echo "usage: $0 {auto|local|hybrid|status} [--verbose]"; exit 2 ;;
esac
