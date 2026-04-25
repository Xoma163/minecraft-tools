#!/bin/bash

set -euo pipefail

if command -v systemctl >/dev/null 2>&1; then
  exec systemctl stop minecraft-admin.service
fi

echo "Use your service manager to stop minecraft-admin." >&2
exit 1
