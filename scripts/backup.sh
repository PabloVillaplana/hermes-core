#!/usr/bin/env bash
# Export every installed Hermes profile (memories, skills, SOUL, config; API keys stripped)
# into a dated folder. Point BACKUP_DIR at a PRIVATE git repo or an encrypted/cloud folder —
# exports contain agent memory, which may include client information.
#
# Usage:
#   scripts/backup.sh                       # all profiles that have a repo folder here
#   BACKUP_DIR=~/HermesBackups scripts/backup.sh percy personal
set -euo pipefail

CORE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ROOT_DIR="$(cd "$CORE_DIR/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$HOME/HermesBackups}"
STAMP="$(date +%Y-%m-%d)"

command -v hermes >/dev/null || { echo "hermes not found in PATH" >&2; exit 1; }

names=("$@")
if [ ${#names[@]} -eq 0 ]; then
  for d in "$ROOT_DIR"/hermes-*; do
    [ -f "$d/distribution.yaml" ] || continue
    names+=("$(awk -F': *' '/^name:/{gsub(/"/,"",$2); print $2; exit}' "$d/distribution.yaml")")
  done
fi

mkdir -p "$BACKUP_DIR/$STAMP"
for p in "${names[@]}"; do
  out="$BACKUP_DIR/$STAMP/$p.tar.gz"
  echo "==> exporting $p -> $out"
  hermes profile export "$p" -o "$out"
done

if git -C "$BACKUP_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$BACKUP_DIR" add "$STAMP"
  git -C "$BACKUP_DIR" commit -q -m "backup: hermes profiles $STAMP" && echo "committed in $BACKUP_DIR (not pushed)"
fi
