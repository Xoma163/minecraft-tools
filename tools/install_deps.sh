#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly INSTALL_DIR="$SCRIPT_DIR/bin"
readonly MCRCON_VERSION="0.7.2"
readonly MCRCON_ARCHIVE_URL="https://github.com/Tiiffi/mcrcon/archive/refs/tags/v${MCRCON_VERSION}.tar.gz"

tmp_dir="$(mktemp -d)"
archive_path="$tmp_dir/mcrcon.tar.gz"
src_dir="$tmp_dir/mcrcon-${MCRCON_VERSION}"

cleanup() {
  rm -rf "$tmp_dir"
}

download_file() {
  local url="$1"
  local output_path="$2"

  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$output_path"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$output_path" "$url"
  else
    echo "curl or wget is required" >&2
    exit 1
  fi
}

install_mcrcon() {
  mkdir -p "$INSTALL_DIR"

  download_file "$MCRCON_ARCHIVE_URL" "$archive_path"
  tar -xzf "$archive_path" -C "$tmp_dir"

  if ! command -v cc >/dev/null 2>&1 && ! command -v gcc >/dev/null 2>&1; then
    echo "C compiler is required to build mcrcon" >&2
    exit 1
  fi

  make -C "$src_dir"
  install -m 0755 "$src_dir/mcrcon" "$INSTALL_DIR/mcrcon"

  echo "Installed mcrcon ${MCRCON_VERSION} to $INSTALL_DIR/mcrcon"
}

trap cleanup EXIT

install_mcrcon
