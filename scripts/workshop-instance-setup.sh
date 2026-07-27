#!/usr/bin/env bash
# Facilitator setup for workshop EC2 instances (run once per AMI/instance).
set -euo pipefail

if ! command -v npx >/dev/null 2>&1; then
  echo "Installing Node.js (required for Splunk MCP via mcp-remote)..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y nodejs npm
  else
    echo "Install Node.js manually so 'npx' is on PATH." >&2
    exit 1
  fi
fi

echo "OK  npx=$(command -v npx)"
npx --version
