#!/usr/bin/env bash
# Install (first time) or update Hermes profiles from the local repo folders.
#
# Usage:
#   scripts/install.sh --all
#   scripts/install.sh percy personal        # by profile name (folder hermes-<name>)
#
# First install creates the profile + its command alias (e.g. `percy chat`)
# and a .env.EXAMPLE you must copy to .env and fill (COMPOSIO_API_KEY, ...).
# Updates keep your memories, sessions, .env and local config.yaml edits.
# To push repo changes in config.yaml too:  FORCE_CONFIG=1 scripts/install.sh percy
set -euo pipefail

CORE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ROOT_DIR="$(cd "$CORE_DIR/.." && pwd)"
HERMES_HOME_ROOT="${HERMES_HOME_ROOT:-$HOME/.hermes}"

command -v hermes >/dev/null || { echo "hermes not found in PATH" >&2; exit 1; }
[ $# -eq 0 ] && { awk 'NR>1 && /^#/{sub(/^# ?/,"");print;next} NR>1{exit}' "$0"; exit 1; }

names=()
if [ "$1" = "--all" ]; then
  for d in "$ROOT_DIR"/hermes-*; do
    [ -f "$d/distribution.yaml" ] || continue
    names+=("$(basename "$d" | sed 's/^hermes-//')")
  done
else
  names=("$@")
fi

# Always rebuild first so SOUL.md and skills/core are current.
dirs=()
for n in "${names[@]}"; do dirs+=("$ROOT_DIR/hermes-$n"); done
"$CORE_DIR/scripts/build.sh" "${dirs[@]}"

for n in "${names[@]}"; do
  dir="$ROOT_DIR/hermes-$n"
  [ -f "$dir/distribution.yaml" ] || { echo "ERROR: $dir/distribution.yaml missing" >&2; exit 1; }
  profile="$(awk -F': *' '/^name:/{gsub(/"/,"",$2); print $2; exit}' "$dir/distribution.yaml")"

  if [ -d "$HERMES_HOME_ROOT/profiles/$profile" ]; then
    echo "==> updating $profile from $dir"
    if [ "${FORCE_CONFIG:-0}" = "1" ]; then
      hermes profile update "$profile" --force-config --yes
    else
      hermes profile update "$profile"
    fi
  else
    echo "==> installing $profile from $dir"
    hermes profile install "$dir" --alias
    env_file="$HERMES_HOME_ROOT/profiles/$profile/.env"
    if [ ! -f "$env_file" ] && [ -f "$env_file.EXAMPLE" ]; then
      echo "    next: cp \"$env_file.EXAMPLE\" \"$env_file\" and fill the keys"
    fi
  fi
done
