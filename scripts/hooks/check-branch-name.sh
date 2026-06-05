#!/usr/bin/env sh
set -eu

branch="$(git branch --show-current)"

if [ -z "$branch" ]; then
  echo "Detached HEAD; skipping branch name check."
  exit 0
fi

if ! printf '%s\n' "$branch" | grep -E '^(feature|fix|docs|chore)/[A-Za-z0-9._-]+$' >/dev/null 2>&1; then
  echo "Invalid branch name: $branch" >&2
  echo "Expected: feature/*, fix/*, docs/*, or chore/*" >&2
  exit 1
fi
