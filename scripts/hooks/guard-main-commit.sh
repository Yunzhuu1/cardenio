#!/usr/bin/env sh
set -eu

branch="$(git branch --show-current)"

case "$branch" in
  main|master)
    echo "Do not commit directly on $branch. Create a topic branch first." >&2
    exit 1
    ;;
esac
