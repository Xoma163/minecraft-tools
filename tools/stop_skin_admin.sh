#!/bin/bash

set -euo pipefail

if command -v systemctl >/dev/null 2>&1; then
  exec systemctl stop minecraft-skins-admin.service
fi

echo "Use your service manager to stop minecraft-skins-admin." >&2
exit 1
