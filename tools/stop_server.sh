#!/bin/bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

load_config
validate_common_config

countdown="${1:-10}"

[[ "$countdown" =~ ^[0-9]+$ ]] || fail "Countdown must be a non-negative integer"

require_executable "$MCRCON_BIN"

if [[ "$countdown" -gt 0 ]]; then
  for ((i=countdown; i>=1; i--)); do
    rcon "say Server stopping in ${i}..."
    sleep 1
  done
fi

rcon "say Server stopping now."
rcon "stop"
