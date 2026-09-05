#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -d .git ]]; then
  git init
fi

if ! git rev-parse HEAD >/dev/null 2>&1; then
  git add .
  git -c user.name="font-format-schema" -c user.email="font-format-schema@invalid" commit -m "Initial font-format-schema scaffold"
fi

uv run fontschema sources subtree-init
