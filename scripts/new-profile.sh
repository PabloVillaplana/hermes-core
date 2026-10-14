#!/usr/bin/env bash
# Scaffold a new profile repo next to hermes-core from templates/profile.
#
# Usage: scripts/new-profile.sh <name> "<one-line description>" [/absolute/working/dir]
# Example: scripts/new-profile.sh acme "Client work for ACME" /Users/me/Proyectos/acme
set -euo pipefail

CORE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ROOT_DIR="$(cd "$CORE_DIR/.." && pwd)"
NAME="${1:?Usage: $0 <name> \"<description>\" [cwd]}"
DESC="${2:?Missing description}"
CWD="${3:-$HOME/Proyectos}"
DEST="$ROOT_DIR/hermes-$NAME"

case "$NAME" in *[!a-z0-9-]*) echo "Name must be lowercase letters, digits or dashes" >&2; exit 1;; esac

mkdir -p "$DEST"
( cd "$CORE_DIR/templates/profile" && find . -type f ) | while read -r rel; do
  rel="${rel#./}"
  dest="$DEST/$rel"
  if [ -e "$dest" ]; then echo "exists  $rel"; continue; fi
  mkdir -p "$(dirname "$dest")"
  sed -e "s|__NAME__|$NAME|g" -e "s|__DESCRIPTION__|$DESC|g" -e "s|__CWD__|$CWD|g" \
    "$CORE_DIR/templates/profile/$rel" > "$dest"
  echo "created $rel"
done

"$CORE_DIR/scripts/build.sh" "$DEST"
echo
echo "Next: edit $DEST/SOUL.local.md, then run: $CORE_DIR/scripts/install.sh $NAME"
