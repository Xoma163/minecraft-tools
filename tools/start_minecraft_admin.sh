#!/bin/bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

load_config
validate_minecraft_admin_config

cd "$MINECRAFT_HOME"
exec uv run uvicorn tools.minecraft_admin.app:app --host 0.0.0.0 --port "$MINECRAFT_ADMIN_PORT"
