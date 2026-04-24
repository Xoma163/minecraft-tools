#!/bin/bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

load_config
validate_common_config

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <backup-file.tar.gz>" >&2
  echo "Example: $0 $BACKUP_DIR/minecraft_2026.04.23_01-00-00.tar.gz" >&2
  exit 1
fi

backup_file="$1"

if [[ ! -f "$backup_file" ]]; then
  echo "Backup file not found: $backup_file" >&2
  exit 1
fi

if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "Backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi

parent_dir="$(dirname "$SERVER_DIR")"
server_dir_name="$(basename "$SERVER_DIR")"
backup_existing="${SERVER_DIR}.before_restore.$(date +"%Y%m%d_%H%M%S")"

echo "Restoring backup: $backup_file"
echo "Target directory: $SERVER_DIR"
echo
echo "IMPORTANT: stop the Minecraft server before restore."

if ! tar -tzf "$backup_file" | grep -q "^${server_dir_name}/"; then
  echo "Backup archive does not contain expected directory: $server_dir_name" >&2
  exit 1
fi

mkdir -p "$parent_dir"

if [[ -d "$SERVER_DIR" ]]; then
  echo "Moving current server directory to: $backup_existing"
  mv "$SERVER_DIR" "$backup_existing"
fi

tar -xzf "$backup_file" -C "$parent_dir"

if [[ ! -d "$SERVER_DIR" ]]; then
  echo "Extracted directory not found after restore: $SERVER_DIR" >&2
  exit 1
fi

echo "Restore completed: $SERVER_DIR"
echo "Previous server directory saved as: $backup_existing"
