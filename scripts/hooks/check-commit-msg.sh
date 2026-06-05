#!/usr/bin/env sh
set -eu

commit_msg_file="${1:-}"

if [ -z "$commit_msg_file" ] || [ ! -f "$commit_msg_file" ]; then
  echo "Commit message file is missing." >&2
  exit 1
fi

subject="$(sed -n '1p' "$commit_msg_file")"

if ! printf '%s\n' "$subject" | grep -E '^(feat|fix|docs|chore|test|refactor|style): .+' >/dev/null 2>&1; then
  echo "Invalid commit message." >&2
  echo "Expected format: type: message" >&2
  echo "Allowed types: feat, fix, docs, chore, test, refactor, style" >&2
  exit 1
fi
