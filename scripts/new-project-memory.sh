#!/usr/bin/env bash
# Add the project-memory skeleton (AGENTS.md + docs/agent/) to a project repo.
# Never overwrites existing files.
#
# Usage: scripts/new-project-memory.sh /path/to/project
set -euo pipefail

CORE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE="$CORE_DIR/templates/project"
TARGET="${1:?Usage: $0 /path/to/project}"
TARGET="$(cd "$TARGET" && pwd)"

( cd "$TEMPLATE" && find . -type f ) | while read -r rel; do
  rel="${rel#./}"
  dest="$TARGET/$rel"
  if [ -e "$dest" ]; then
    echo "exists  $rel"
  else
    mkdir -p "$(dirname "$dest")"
    cp "$TEMPLATE/$rel" "$dest"
    echo "created $rel"
  fi
done

echo
echo "Next: open a Hermes session in $TARGET and ask it to fill the TODOs"
echo "(it will use the project-memory skill), then commit: docs: add agent project memory"
