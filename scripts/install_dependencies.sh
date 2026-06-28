#!/usr/bin/env bash
# Create Python venv on Mac and install deps. Safe to run repeatedly.
# Run with: bash scripts/install_dependencies.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY_BIN=""

# Source pyenv shims into this non-interactive shell if available.
if [ -d "$HOME/.pyenv" ] && [ -z "${PYENV_ROOT:-}" ]; then
  export PYENV_ROOT="$HOME/.pyenv"
  export PATH="$PYENV_ROOT/bin:$PATH"
fi

if command -v pyenv >/dev/null 2>&1; then
  # Prefix-match: prefer 3.11.x, then 3.12.x, then 3.10.x
  for prefix in 3.11 3.12 3.10; do
    match=$(pyenv versions --bare 2>/dev/null | awk -v p="$prefix" 'index($0,p)==1 {print; exit}')
    if [ -n "$match" ]; then
      PY_BIN="$(pyenv root)/versions/$match/bin/python"
      [ -x "$PY_BIN" ] && break || PY_BIN=""
    fi
  done
fi

if [ -z "$PY_BIN" ]; then
  SYS_VER=$(python3 -c 'import sys; print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo "")
  case "$SYS_VER" in
    3.10|3.11|3.12) PY_BIN="$(command -v python3)" ;;
    *) echo "ERROR: need Python 3.10-3.12 (have $SYS_VER). Install with: pyenv install 3.11.9" >&2; exit 2 ;;
  esac
fi
echo "[install] using $PY_BIN ($("$PY_BIN" --version))"

if [ ! -d "$ROOT/.venv" ]; then
  "$PY_BIN" -m venv "$ROOT/.venv"
  echo "[install] created .venv"
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
python -m pip install --upgrade pip wheel setuptools

if [ ! -f "$ROOT/requirements.txt" ]; then
  echo "ERROR: requirements.txt missing" >&2
  exit 3
fi

pip install -r "$ROOT/requirements.txt"
echo
echo "[install] OK. Activate with:  source .venv/bin/activate"
