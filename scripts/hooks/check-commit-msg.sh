#!/usr/bin/env sh
set -eu

commit_msg_file="${1:-}"

if [ -z "$commit_msg_file" ] || [ ! -f "$commit_msg_file" ]; then
  echo "Commit message file is missing." >&2
  exit 1
fi

subject="$(sed -n '1p' "$commit_msg_file")"

if ! printf '%s\n' "$subject" | grep -E '^(feat|fix|docs|chore|test|refactor|style)(\([A-Za-z0-9._-]+\))?: .+' >/dev/null 2>&1; then
  echo "Invalid commit message." >&2
  echo "Expected format: type: message or type(scope): message" >&2
  echo "Allowed types: feat, fix, docs, chore, test, refactor, style" >&2
  exit 1
fi

if printf '%s\n' "$subject" | LC_ALL=C grep '[^ -~]' >/dev/null 2>&1; then
  echo "Invalid commit message." >&2
  echo "Commit subject must be written in ASCII English." >&2
  echo "Do not use full-width punctuation such as ， 。 ：" >&2
  exit 1
fi
