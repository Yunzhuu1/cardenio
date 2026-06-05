#!/usr/bin/env sh
set -eu

branch="$(git branch --show-current)"

if [ -z "$branch" ]; then
  echo "Detached HEAD; skipping branch name check."
  exit 0
fi

if printf '%s\n' "$branch" | grep -E '^(main|master|develop)$' >/dev/null 2>&1; then
  exit 0
fi

if ! printf '%s\n' "$branch" | grep -E '^(feature|feat|bugfix|fix|hotfix|release|chore)/[a-z0-9]+(\.[a-z0-9]+)*(-[a-z0-9]+(\.[a-z0-9]+)*)*$' >/dev/null 2>&1; then
  echo "Invalid branch name: $branch" >&2
  echo "Expected Conventional Branch format: <type>/<description>" >&2
  echo "Allowed types: feature, feat, bugfix, fix, hotfix, release, chore" >&2
  echo "Description must use lowercase letters, numbers, hyphens, and dots without leading, trailing, or consecutive separators." >&2
  exit 1
fi
