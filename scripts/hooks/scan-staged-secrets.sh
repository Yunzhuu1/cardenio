#!/usr/bin/env sh
set -eu

staged_files="$(git diff --cached --name-only --diff-filter=ACMR)"

if [ -z "$staged_files" ]; then
  exit 0
fi

echo "$staged_files" | grep -E '(^|/)\.env(\..*)?$' | grep -vE '(^|/)\.env\.example$' >/dev/null 2>&1 && {
  echo "Refusing to commit .env files. Commit .env.example instead." >&2
  exit 1
}

if git diff --cached --unified=0 | grep -E '^\+' | grep -E '((SECRET|TOKEN|API[_-]?KEY|PRIVATE[_-]?KEY|PASSWORD)[A-Za-z0-9_-]*[[:space:]]*[:=][[:space:]]*[^[:space:]]+|BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY)' >/dev/null 2>&1; then
  echo "Potential secret detected in staged changes. Remove it before committing." >&2
  exit 1
fi
