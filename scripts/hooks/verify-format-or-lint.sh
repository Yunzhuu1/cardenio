#!/usr/bin/env sh
set -eu

if [ ! -f package.json ]; then
  echo "No package.json found; skipping lint/format check."
  exit 0
fi

if node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts.lint ? 0 : 1)" >/dev/null 2>&1; then
  pnpm run lint
  exit 0
fi

if node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts['format:check'] ? 0 : 1)" >/dev/null 2>&1; then
  pnpm run format:check
  exit 0
fi

echo "No lint or format:check script found; skipping lint/format check."
