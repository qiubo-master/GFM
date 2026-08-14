#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/root/autodl-tmp/AI-Foundation}"
DATA_ROOT="${DATA_ROOT:-/root/autodl-tmp/ai-foundation-data}"
LOG_ROOT="${LOG_ROOT:-/root/autodl-tmp/logs}"
APP_PORT="${APP_PORT:-6008}"
VENV_DIR="${VENV_DIR:-.venv-gpu}"

mkdir -p "$DATA_ROOT" "$LOG_ROOT"
cd "$APP_ROOT"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  /root/miniconda3/bin/python -m venv --system-site-packages "$VENV_DIR"
  "$VENV_DIR/bin/python" -m pip install -e . ultralytics paddleocr paddlepaddle
fi

if [[ -z "${FOUNDATION_API_KEYS:-}" ]]; then
  echo "FOUNDATION_API_KEYS is required" >&2
  exit 1
fi

FOUNDATION_MODE="${FOUNDATION_MODE:-real}" \
FOUNDATION_API_KEYS="$FOUNDATION_API_KEYS" \
FOUNDATION_DATA_DIR="$DATA_ROOT" \
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}" \
VISION_OLLAMA_BASE_URL="${VISION_OLLAMA_BASE_URL:-http://127.0.0.1:11435}" \
TEXT_MODEL="${TEXT_MODEL:-qwen3:8b}" \
EMBED_MODEL="${EMBED_MODEL:-qwen3-embedding:0.6b}" \
VISION_MODEL="${VISION_MODEL:-qwen3-vl:4b-instruct-q4_K_M}" \
YOLO_MODEL="${YOLO_MODEL:-/root/autodl-tmp/models/yolo11n.pt}" \
  nohup "$VENV_DIR/bin/python" -m uvicorn foundation.main:app \
    --host 0.0.0.0 --port "$APP_PORT" \
    >>"$LOG_ROOT/ai-foundation.out.log" \
    2>>"$LOG_ROOT/ai-foundation.err.log" < /dev/null &

echo $! > "$DATA_ROOT/ai-foundation.pid"

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:$APP_PORT/foundation/v1/health"; then
    echo
    echo "AI Foundation is running on port $APP_PORT"
    exit 0
  fi
  sleep 1
done

echo "AI Foundation failed to start; see $LOG_ROOT/ai-foundation.err.log" >&2
exit 1
