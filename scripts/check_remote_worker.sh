#!/usr/bin/env bash
# Probe the Ubuntu worker. Read-only. Run with: bash scripts/check_remote_worker.sh
set -u
RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; RST=$'\e[0m'
ok()   { printf "  ${GRN}OK${RST}    %s\n" "$1"; }
warn() { printf "  ${YEL}WARN${RST}  %s\n" "$1"; }
miss() { printf "  ${RED}MISS${RST}  %s\n" "$1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CFG="$ROOT/config/remote_worker.yaml"

USER=$(awk -F': *' '/^user:/   {gsub(/"/, "", $2); print $2}' "$CFG")
IP=$(  awk -F': *' '/^ip:/     {gsub(/"/, "", $2); print $2}' "$CFG")
TARGET="${USER}@${IP}"

echo "=== check_remote_worker.sh -> $TARGET ==="

if ping -c 1 -W 2000 "$IP" >/dev/null 2>&1; then ok "ping $IP"
else miss "ping $IP failed"; exit 1; fi

if ssh -o ConnectTimeout=8 -o BatchMode=yes "$TARGET" "true" 2>/dev/null; then ok "ssh $TARGET (key auth)"
else miss "ssh $TARGET failed — check ssh agent / authorized_keys"; exit 2; fi

echo
echo "[remote info]"
ssh -o ConnectTimeout=8 -o BatchMode=yes "$TARGET" '
  echo "  hostname : $(hostname)"
  echo "  os       : $(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY | cut -d= -f2 | tr -d \")"
  echo "  arch     : $(uname -m)"
  echo "  kernel   : $(uname -r)"
  echo "  cores    : $(nproc)"
  echo "  ram GB   : $(awk "/MemTotal/{printf \"%.0f\", \$2/1024/1024}" /proc/meminfo)"
  echo "  free GB  : $(df -h $HOME | awk "NR==2 {print \$4}")"
'

echo
echo "[gpu]"
if ssh -o ConnectTimeout=8 -o BatchMode=yes "$TARGET" "command -v nvidia-smi >/dev/null"; then
  ssh -o ConnectTimeout=8 -o BatchMode=yes "$TARGET" "nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader" | sed 's/^/  /'
else
  warn "no nvidia-smi on worker"
fi

echo
echo "[ollama]"
if ssh -o ConnectTimeout=8 -o BatchMode=yes "$TARGET" "command -v ollama >/dev/null"; then
  ssh -o ConnectTimeout=8 -o BatchMode=yes "$TARGET" "ollama --version" | sed 's/^/  /'
  STATE=$(ssh -o ConnectTimeout=8 -o BatchMode=yes "$TARGET" "systemctl is-active ollama 2>/dev/null || echo unknown")
  echo "  systemd  : $STATE"
  BIND=$(ssh -o ConnectTimeout=8 -o BatchMode=yes "$TARGET" "ss -tln 2>/dev/null | awk '/:11434/{print \$4; exit}'")
  if [ -n "$BIND" ]; then
    case "$BIND" in
      127.0.0.1:11434) ok "ollama bound to localhost only (use SSH tunnel)";;
      \*:11434|0.0.0.0:11434) warn "ollama bound to ALL interfaces — see docs/11-privacy-checklist.md";;
      "${IP}:11434") ok "ollama bound to ${IP}:11434 (LAN). Firewall should allow Mac only.";;
      *) warn "unexpected bind: $BIND";;
    esac
  else
    warn "port 11434 not listening on worker"
  fi
  echo "  models:"
  ssh -o ConnectTimeout=8 -o BatchMode=yes "$TARGET" "ollama list" 2>/dev/null | sed 's/^/    /'
else
  miss "ollama not installed on worker"
fi

echo
echo "Done."
