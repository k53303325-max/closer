#!/usr/bin/env bash
# Create private GitHub repo and push (needs: gh auth login)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
GH="${GH_BIN:-gh}"
if ! command -v "$GH" >/dev/null 2>&1; then
  echo "Install gh: https://cli.github.com/"
  exit 1
fi
"$GH" auth status
"$GH" repo create closer-deal --private --source=. --remote=origin --push
