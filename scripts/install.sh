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
#
# Every run also (re)installs the financial-guard hook to ~/.hermes/agent-hooks/, makes sure each
# installed profile's config.yaml declares it, approves it for that profile, and verifies it.
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

# Financial guard: test it, then install it before any profile can use it.
GUARD_SRC="$CORE_DIR/hooks/financial-guard.py"
GUARD_DST="$HERMES_HOME_ROOT/agent-hooks/financial-guard.py"
GUARD_CMD="~/.hermes/agent-hooks/financial-guard.py"   # exact string used in config.yaml
python3 "$CORE_DIR/hooks/test_financial_guard.py" >/dev/null || {
  echo "ERROR: financial-guard tests failed; run python3 $CORE_DIR/hooks/test_financial_guard.py" >&2; exit 1; }
mkdir -p "$(dirname "$GUARD_DST")"
cp "$GUARD_SRC" "$GUARD_DST" && chmod 755 "$GUARD_DST"
echo '{"tool_name":"terminal","tool_input":{"command":"stripe charges create --live"}}' | "$GUARD_DST" \
  | grep -q '"block"' || { echo "ERROR: $GUARD_DST does not run (python3 missing?)" >&2; exit 1; }
echo "financial-guard installed at $GUARD_DST"

ensure_guard() {  # $1 = profile name
  local home="$HERMES_HOME_ROOT/profiles/$1" cfg
  cfg="$home/config.yaml"
  [ -f "$cfg" ] || { echo "WARN: $cfg not found" >&2; return; }
  if ! grep -q "financial-guard" "$cfg"; then
    if grep -qE '^hooks:' "$cfg"; then
      echo "ERROR: $cfg already has a hooks: block without financial-guard. Add it by hand or rerun with FORCE_CONFIG=1." >&2
      exit 1
    fi
    printf '%s\n' "" \
      "# Financial guard (added by hermes-core/scripts/install.sh)" \
      "hooks:" \
      "  pre_tool_call:" \
      "    - command: \"$GUARD_CMD\"" \
      "      timeout: 10" \
      "      fail_closed: true" >> "$cfg"
    echo "    added financial-guard hook to $cfg"
  fi
  # Approve the hook for this profile so CLI, dashboard and gateway sessions register it.
  python3 - "$home/shell-hooks-allowlist.json" "$GUARD_CMD" <<'PY'
import datetime, json, os, sys
path, command = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(path))
    assert isinstance(data.get("approvals"), list)
except Exception:
    data = {"approvals": []}
if not any(e.get("event") == "pre_tool_call" and e.get("command") == command for e in data["approvals"]):
    data["approvals"].append({"event": "pre_tool_call", "command": command,
                              "approved_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    print("    approved financial-guard for this profile")
PY
  if hermes -p "$1" hooks list 2>/dev/null | grep -q "financial-guard"; then
    echo "    financial-guard active for $1"
  else
    echo "WARN: 'hermes -p $1 hooks list' does not show financial-guard — run 'hermes -p $1 hooks doctor'" >&2
  fi
}

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
  ensure_guard "$profile"
done
