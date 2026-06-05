#!/usr/bin/env sh
set -eu

branch="$(git branch --show-current)"

case "$branch" in
  main|master)
    echo "Do not push directly to $branch. Push a topic branch and open a PR." >&2
    exit 1
    ;;
esac
