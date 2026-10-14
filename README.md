# hermes-core

Shared rules, skills and tooling for all of Villa's [Hermes Agent](https://github.com/NousResearch/hermes-agent) profiles.

```
AI Profiles/
├── hermes-core/        # this repo — shared rules + scripts (not installed as a profile)
├── hermes-percy/       # Percy / Buyside (Buyermls)
├── hermes-datacor/     # Datacorp
├── hermes-mythic/      # Mythic
└── hermes-personal/    # own ventures + personal life
```

Each `hermes-<name>` folder is a **Hermes profile distribution**: a git repo that Hermes installs as an isolated profile (own config, `.env`, SOUL, memory, sessions, skills) with its own command (`percy chat`, `personal chat`, …).

## Three layers of knowledge

| Layer | Lives in | Versioned | Contains |
|-------|----------|-----------|----------|
| **Rules** | these repos (`SOUL.md`, `config.yaml`, `skills/`) | git | How each agent behaves, which apps it may use |
| **Project memory** | each project repo: `AGENTS.md` + `docs/agent/` | git, with the code | Architecture, decisions (ADRs), gotchas, handoffs |
| **Agent memory** | `~/.hermes/profiles/<name>/memories/` | backups via `scripts/backup.sh` | Preferences and habits the agent learns |

Project facts belong in the project repo, so they survive any tool change and are reviewed in PRs. Hermes' own memory is size-capped and gets consolidated, so it is not the source of truth.

## How SOUL.md is built

Distributions do not inherit from each other, so core rules are composed in at build time:

```
SOUL.md = hermes-core/SOUL.base.md  +  hermes-<name>/SOUL.local.md
skills/core/ = copy of hermes-core/skills/
```

`SOUL.md` and `skills/core/` are **generated and committed** (so each repo is installable on its own). Never edit them directly.

## Daily workflow

```bash
cd ~/Proyectos/"AI Profiles"

# Change shared rules or skills
$EDITOR hermes-core/SOUL.base.md
./hermes-core/scripts/build.sh --all        # regenerate every profile
./hermes-core/scripts/install.sh --all      # push changes into ~/.hermes/profiles/*

# Change one profile
$EDITOR hermes-percy/SOUL.local.md
./hermes-core/scripts/install.sh percy      # builds + updates that profile
```

`install.sh` installs a profile the first time (creating the `percy` command) and updates it afterwards. Updates keep memories, sessions, `.env` and local `config.yaml` edits. To push repo changes to `config.yaml` as well: `FORCE_CONFIG=1 ./hermes-core/scripts/install.sh percy`.

Changes take effect in **new** sessions (SOUL and memory are loaded at session start).

## First-time setup

```bash
cd ~/Proyectos/"AI Profiles"
chmod +x hermes-core/scripts/*.sh

# 1. Git repos (add --github to create private GitHub repos and push)
./hermes-core/scripts/init-git.sh

# 2. Install all profiles
./hermes-core/scripts/install.sh --all

# 3. Per profile: add its own Composio key
cp ~/.hermes/profiles/percy/.env.EXAMPLE ~/.hermes/profiles/percy/.env
$EDITOR ~/.hermes/profiles/percy/.env       # COMPOSIO_API_KEY=...

# 4. Check
percy doctor
percy chat
```

Model access reuses the OAuth logins in the root `~/.hermes/auth.json` (Anthropic, OpenAI), so profiles do not need their own login. To give one profile a separate login: `hermes -p percy auth add <provider>`.

## Composio: one environment per profile

Every profile's `config.yaml` points to Composio Connect MCP with the key from **that profile's** `.env`:

```yaml
mcp_servers:
  composio:
    url: "https://connect.composio.dev/mcp"
    headers:
      x-consumer-api-key: "${COMPOSIO_API_KEY}"
```

Use a separate Composio user/account per profile and connect only the apps that profile needs (e.g. Percy → Buyermls Jira; Personal → personal Gmail, WhatsApp Business). That way an agent can never act through another context's accounts.

Prefer the MCP route over the Composio CLI: CLI credentials live in your real `$HOME` and would be shared by every profile.

## Project memory for a repo

```bash
./hermes-core/scripts/new-project-memory.sh /Users/pablovillaplana/Buyside/hvs
```

Adds `AGENTS.md` and `docs/agent/{context.md,gotchas.md,decisions/,handoffs/}` without overwriting anything. Then open a session there and ask the agent to fill the TODOs (`project-memory` skill). Hermes loads `AGENTS.md` from the working directory automatically; Claude Code and Codex read it too.

## Backups of agent memory

```bash
./hermes-core/scripts/backup.sh                   # → ~/HermesBackups/YYYY-MM-DD/<profile>.tar.gz
BACKUP_DIR=~/somewhere ./hermes-core/scripts/backup.sh percy
```

Exports contain agent memory (possibly client information) — keep `BACKUP_DIR` in a **private** git repo or encrypted storage, never in these distribution repos. If `BACKUP_DIR` is a git repo, the script commits (but does not push).

## Adding a new profile

```bash
./hermes-core/scripts/new-profile.sh acme "Client work for ACME" /Users/pablovillaplana/Proyectos/acme
$EDITOR hermes-acme/SOUL.local.md
./hermes-core/scripts/install.sh acme
```

## Important limits

- **Profiles are not sandboxes.** With the `local` terminal backend every profile has your user's full filesystem access; the scope rules in SOUL are guidance, not enforcement. Use a Docker backend for hard isolation.
- **Never run two agent processes on the same profile** — they overwrite each other's memory.
- `.env`, `auth.json`, `memories/`, `sessions/` are ignored by git and stripped by the installer anyway.

## Shared skills

| Skill | Purpose |
|-------|---------|
| `project-memory` | Bootstrap/update `AGENTS.md` + `docs/agent/`, write ADRs and gotchas |
| `session-handoff` | Write an end-of-session handoff into `docs/agent/handoffs/` |
