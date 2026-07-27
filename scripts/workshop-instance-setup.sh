#!/usr/bin/env bash
# Facilitator setup for workshop EC2 instances (run once per AMI/instance).
#
# Installs Node.js 20 (mcp-remote requires Node 18+) and pre-installs mcp-remote
# so the first troubleshooting-agent mcp-doctor run is faster.
set -euo pipefail

MIN_NODE_MAJOR=18

node_major() {
  if ! command -v node >/dev/null 2>&1; then
    echo 0
    return
  fi
  node --version | sed -E 's/^v([0-9]+).*/\1/'
}

install_node_20() {
  if ! command -v curl >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y curl ca-certificates
  fi
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
}

major="$(node_major)"
if [ "$major" -lt "$MIN_NODE_MAJOR" ]; then
  echo "Installing Node.js 20 (current: $(node --version 2>/dev/null || echo missing))..."
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "Install Node.js 20 manually so 'node' and 'npx' are on PATH." >&2
    exit 1
  fi
  install_node_20
fi

echo "OK  node=$(node --version)  npx=$(command -v npx)"
echo "Pre-installing mcp-remote..."
sudo npm install -g mcp-remote
echo "OK  mcp-remote installed"
