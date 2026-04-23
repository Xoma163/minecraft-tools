#!/bin/bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

load_config
validate_common_config

cd "$SERVER_DIR"
exec ./run.sh
