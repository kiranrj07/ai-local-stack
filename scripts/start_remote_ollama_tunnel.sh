#!/usr/bin/env bash
# Open SSH tunnel: Mac:11435 -> Ubuntu:11434. Idempotent.
# Run with: bash scripts/start_remote_ollama_tunnel.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$ROOT/config/remote_worker.yaml"
USER=$(awk -F': *' '/^user:/{gsub(/"/,"",$2); print $2}' "$CFG")
IP=$(  awk -F': *' '/^ip:/  {gsub(/"/,"",$2); print $2}' "$CFG")
TARGET="${USER}@${IP}"
LOCAL_PORT=11435

if lsof -nP -iTCP:"$LOCAL_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if curl -fsS "http://localhost:${LOCAL_PORT}/api/tags" >/dev/null 2>&1; then
    echo "tunnel already open: http://localhost:${LOCAL_PORT}"
    exit 0
  fi
  echo "ERROR: port ${LOCAL_PORT} is in use by another process." >&2
  echo "       lsof -nP -iTCP:${LOCAL_PORT} -sTCP:LISTEN" >&2
  exit 1
fi

mkdir -p "$ROOT/logs"
LOGFILE="$ROOT/logs/ssh_tunnel.log"

echo "starting tunnel: localhost:${LOCAL_PORT} -> ${TARGET}:11434"
ssh -f -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    -L "${LOCAL_PORT}:localhost:11434" "$TARGET" \
    >> "$LOGFILE" 2>&1

sleep 1
if curl -fsS "http://localhost:${LOCAL_PORT}/api/tags" >/dev/null 2>&1; then
  echo "OK. test: curl http://localhost:${LOCAL_PORT}/api/tags"
else
  echo "WARN: tunnel started but /api/tags not reachable. Check $LOGFILE" >&2
  exit 2
fi
