#!/bin/bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

load_config
validate_common_config

SAVE_DISABLED=0

cleanup() {
  if [[ "$SAVE_DISABLED" -eq 1 ]]; then
    rcon "save-on" || true
  fi
}

trap cleanup EXIT

require_executable "$MCRCON_BIN"

if [[ ! -d "$SERVER_DIR" ]]; then
  echo "Server directory not found: $SERVER_DIR" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

rcon "say Start backup."
rcon "save-off"
SAVE_DISABLED=1
rcon "save-all"

dt="$(date +"%Y.%m.%d_%H-%M-%S")"
archive_path="$BACKUP_DIR/minecraft_${dt}.tar.gz"

echo "$dt"
echo "Creating backup: $archive_path"

tar -czf "$archive_path" -C "$(dirname "$SERVER_DIR")" "$(basename "$SERVER_DIR")"
find "$BACKUP_DIR" -type f \( -name '*.tar.gz' -o -name '*.gz' \) -mtime +"$BACKUP_RETENTION_DAYS" -print -delete

rcon "save-on"
SAVE_DISABLED=0
rcon "say Backup complete, glhf <3"
