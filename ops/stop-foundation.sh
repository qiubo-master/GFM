#!/usr/bin/env bash
set -euo pipefail

PID_FILE="${DATA_ROOT:-/root/autodl-tmp/ai-foundation-data}/ai-foundation.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "AI Foundation is not running"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" 2>/dev/null; then
  kill -TERM "$PID"
fi
rm -f "$PID_FILE"
echo "AI Foundation stopped"

