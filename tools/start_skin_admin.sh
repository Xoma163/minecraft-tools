#!/bin/bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

load_config
validate_skin_admin_config

cd "$MINECRAFT_HOME"
exec uv run uvicorn tools.skin_admin.app:app --host 127.0.0.1 --port 8010
