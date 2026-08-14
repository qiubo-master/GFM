#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/autodl-tmp/GFM"
RELEASES="$ROOT/releases"
SHARED="$ROOT/shared"
CURRENT="$ROOT/current"
ARCHIVE="/tmp/gfm-${RELEASE_SHA:-}.tgz"

mkdir -p "$RELEASES" "$SHARED" /root/autodl-tmp/logs

if [[ "${ACTION:-deploy}" == "rollback" ]]; then
  current_target="$(readlink -f "$CURRENT" 2>/dev/null || true)"
  target="$(find "$RELEASES" -mindepth 1 -maxdepth 1 -type d ! -path "$current_target" -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)"
  [[ -n "$target" ]] || { echo "No previous GFM release available" >&2; exit 1; }
else
  [[ -f "$ARCHIVE" ]] || { echo "Release archive is missing: $ARCHIVE" >&2; exit 1; }
  target="$RELEASES/$RELEASE_SHA"
  rm -rf "$target"
  mkdir -p "$target"
  tar -xzf "$ARCHIVE" -C "$target"
fi

[[ -f "$SHARED/.env" ]] || { echo "Missing protected configuration: $SHARED/.env" >&2; exit 1; }
ln -sfn /root/autodl-tmp/AI-Foundation/.venv-gpu "$target/.venv-gpu"
set -a
source "$SHARED/.env"
set +a

pid_file="/root/autodl-tmp/ai-foundation-data/ai-foundation.pid"
if [[ -f "$pid_file" ]]; then
  old_pid="$(cat "$pid_file")"
  kill "$old_pid" 2>/dev/null || true
  for _ in $(seq 1 20); do kill -0 "$old_pid" 2>/dev/null || break; sleep 0.5; done
fi

APP_ROOT="$target" DATA_ROOT=/root/autodl-tmp/ai-foundation-data VENV_DIR=.venv-gpu \
  bash "$target/ops/start-foundation.sh"
ln -sfn "$target" "$CURRENT"
printf '%s\n' "$RELEASE_SHA" > "$SHARED/deployed-version"
