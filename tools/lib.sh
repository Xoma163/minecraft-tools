#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="${MINECRAFT_ENV_FILE:-$ROOT_DIR/minecraft.env}"

fail() {
  echo "$*" >&2
  exit 1
}

load_config() {
  [[ -f "$CONFIG_FILE" ]] || fail "Config file not found: $CONFIG_FILE"

  set -a
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
  set +a
}

require_vars() {
  local name

  for name in "$@"; do
    [[ -n "${!name:-}" ]] || fail "Required config variable is missing: $name"
  done
}

validate_common_config() {
  require_vars \
    MINECRAFT_HOME \
    SERVER_NAME \
    SERVER_DIR \
    TOOLS_DIR \
    SERVICE_DIR \
    BACKUP_DIR \
    BACKUP_RETENTION_DAYS \
    MCRCON_BIN \
    RCON_HOST \
    RCON_PORT \
    RCON_PASSWORD
}

require_executable() {
  local path="$1"
  [[ -x "$path" ]] || fail "Executable not found or not executable: $path"
}

rcon() {
  "$MCRCON_BIN" -H "$RCON_HOST" -P "$RCON_PORT" -p "$RCON_PASSWORD" "$1"
}
