#!/usr/bin/env bash
set -euo pipefail

mkdir -p dist

# Ensure pex is available
if ! command -v pex >/dev/null 2>&1; then
  python3 -m pip install --user pex
fi

# Build PEX including local source tree and dependencies
pex -D . -r requirements.txt -m app -o dist/bot.pex

echo "Built dist/bot.pex"

