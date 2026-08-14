#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-deploy}"
RELEASE_SHA="${2:-}"
ROOT=/root/autodl-tmp/GFM
RELEASES="$ROOT/releases"
SHARED="$ROOT/shared"
STATUS="$SHARED/deploy-status.json"
CURRENT="$ROOT/current"

write_status() {
  printf '{"status":"%s","action":"%s","sha":"%s","updated_at":"%s"}\n' \
    "$1" "$ACTION" "$RELEASE_SHA" "$(date -Iseconds)" > "$STATUS"
}
trap 'write_status failed' ERR
write_status processing
mkdir -p "$RELEASES" "$SHARED"

if [[ "$ACTION" == "rollback" ]]; then
  current_target="$(readlink -f "$CURRENT" 2>/dev/null || true)"
  target="$(find "$RELEASES" -mindepth 1 -maxdepth 1 -type d ! -path "$current_target" -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)"
  [[ -n "$target" ]]
  RELEASE_SHA="$(basename "$target")"
else
  [[ -f /etc/network_turbo ]] && source /etc/network_turbo
  target="$RELEASES/$RELEASE_SHA"
  rm -rf "$target"
  mkdir -p "$target"
  archive="/tmp/gfm-$RELEASE_SHA.tar.gz"
  curl --fail --location --retry 10 --retry-all-errors --connect-timeout 20 \
    "https://codeload.github.com/qiubo-master/GFM/tar.gz/$RELEASE_SHA" -o "$archive"
  tar -xzf "$archive" --strip-components=1 -C "$target"
fi

[[ -s "$SHARED/.env" ]]
ln -sfn /root/autodl-tmp/AI-Foundation/.venv-gpu "$target/.venv-gpu"
set -a; source "$SHARED/.env"; set +a
pid_file=/root/autodl-tmp/ai-foundation-data/ai-foundation.pid
if [[ -s "$pid_file" ]]; then
  old_pid="$(cat "$pid_file")"
  kill "$old_pid" 2>/dev/null || true
  for _ in $(seq 1 20); do kill -0 "$old_pid" 2>/dev/null || break; sleep 0.5; done
fi
APP_ROOT="$target" DATA_ROOT=/root/autodl-tmp/ai-foundation-data VENV_DIR=.venv-gpu bash "$target/ops/start-foundation.sh"
ln -sfn "$target" "$CURRENT"
printf '%s\n' "$RELEASE_SHA" > "$SHARED/deployed-version"
write_status success
