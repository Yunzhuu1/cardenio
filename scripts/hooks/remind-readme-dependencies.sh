#!/usr/bin/env sh
set -eu

changed_files="$(git diff --cached --name-only --diff-filter=ACMR)"

if [ -z "$changed_files" ]; then
  exit 0
fi

if echo "$changed_files" | grep -E '(^|/)(package\.json|pnpm-lock\.yaml|package-lock\.json|yarn\.lock|bun\.lockb|bun\.lock|requirements\.txt|pyproject\.toml|poetry\.lock|go\.mod|go\.sum|Cargo\.toml|Cargo\.lock)$' >/dev/null 2>&1; then
  if ! echo "$changed_files" | grep -E '(^|/)README\.md$' >/dev/null 2>&1; then
    echo "Dependency files changed. Confirm README.md documents dependencies and original functionality boundaries." >&2
  fi
fi
