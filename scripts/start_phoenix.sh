#!/usr/bin/env bash
# Start Arize Phoenix locally on the Mac. Run with: bash scripts/start_phoenix.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
[ -d ".venv" ] && source .venv/bin/activate
if ! python -c "import phoenix" 2>/dev/null; then
  echo "arize-phoenix not installed. pip install arize-phoenix" >&2; exit 2
fi
mkdir -p logs
exec python -m phoenix.server.main serve
