#!/usr/bin/env sh
set -eu

if [ ! -f package.json ]; then
  echo "No package.json found; skipping project verification."
  exit 0
fi

if node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts.test ? 0 : 1)" >/dev/null 2>&1; then
  pnpm run test
  exit 0
fi

if node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts.build ? 0 : 1)" >/dev/null 2>&1; then
  pnpm run build
  exit 0
fi

echo "No test or build script found; skipping project verification."
