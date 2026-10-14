#!/usr/bin/env bash
# Initialize every hermes-* folder as its own git repo with a first commit.
# Optionally create PRIVATE GitHub repos and push (requires the gh CLI, logged in).
#
# Usage:
#   scripts/init-git.sh                 # git init + first commit only
#   scripts/init-git.sh --github        # also: gh repo create <owner>/<folder> --private --push
#   GH_OWNER=my-org scripts/init-git.sh --github
set -euo pipefail

CORE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ROOT_DIR="$(cd "$CORE_DIR/.." && pwd)"
GITHUB=0; [ "${1:-}" = "--github" ] && GITHUB=1

"$CORE_DIR/scripts/build.sh" --all

for dir in "$ROOT_DIR"/hermes-*; do
  [ -d "$dir" ] || continue
  repo="$(basename "$dir")"
  if [ ! -d "$dir/.git" ]; then
    git -C "$dir" init -q -b main
    git -C "$dir" add -A
    git -C "$dir" commit -q -m "chore: initial scaffold"
    echo "initialized $repo"
  else
    echo "already a repo: $repo"
  fi

  if [ $GITHUB -eq 1 ] && ! git -C "$dir" remote get-url origin >/dev/null 2>&1; then
    command -v gh >/dev/null || { echo "gh CLI not found" >&2; exit 1; }
    target="${GH_OWNER:+$GH_OWNER/}$repo"
    ( cd "$dir" && gh repo create "$target" --private --source . --push )
    echo "pushed $repo -> github.com/$target (private)"
  fi
done
