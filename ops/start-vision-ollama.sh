#!/usr/bin/env bash
set -euo pipefail

OLLAMA_ROOT="${OLLAMA_ROOT:-/root/autodl-tmp/ollama-latest-candidate}"
MODEL_ROOT="${MODEL_ROOT:-/root/autodl-tmp/models}"
LOG_ROOT="${LOG_ROOT:-/root/autodl-tmp/logs}"
VISION_OLLAMA_HOST="${VISION_OLLAMA_HOST:-127.0.0.1:11435}"

mkdir -p "$LOG_ROOT" "$MODEL_ROOT"

if curl -fsS "http://$VISION_OLLAMA_HOST/api/version" >/dev/null 2>&1; then
  echo "Vision Ollama is already running"
  exit 0
fi

source /etc/network_turbo >/dev/null 2>&1 || true
OLLAMA_MODELS="$MODEL_ROOT" \
OLLAMA_HOST="$VISION_OLLAMA_HOST" \
OLLAMA_LLM_LIBRARY="${OLLAMA_LLM_LIBRARY:-cuda_v12}" \
  nohup "$OLLAMA_ROOT/bin/ollama" serve \
    >>"$LOG_ROOT/ollama-vision.out.log" \
    2>>"$LOG_ROOT/ollama-vision.err.log" < /dev/null &

for _ in $(seq 1 30); do
  if curl -fsS "http://$VISION_OLLAMA_HOST/api/version"; then
    echo
    echo "Vision Ollama is running on $VISION_OLLAMA_HOST"
    exit 0
  fi
  sleep 1
done

echo "Vision Ollama failed to start" >&2
exit 1
