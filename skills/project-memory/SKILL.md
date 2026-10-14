---
name: project-memory
description: Bootstrap or update the in-repo project memory (AGENTS.md + docs/agent/) — use when starting work in a repo that lacks it, when recording a decision (ADR), or when adding a gotcha.
version: 1.0.0
metadata:
  hermes:
    tags: [memory, documentation, adr]
    category: core
---

# Project memory

Project knowledge lives in the repository so it never gets lost and can be reviewed in git.

## Layout

```
<repo>/
├── AGENTS.md                    # Entry point: what the project is, how to run it, rules
└── docs/agent/
    ├── context.md               # Domain, architecture, environments, key people/systems
    ├── gotchas.md               # Non-obvious traps, one bullet each, newest first
    ├── decisions/
    │   ├── 0000-template.md
    │   └── NNNN-short-title.md  # One ADR per decision
    └── handoffs/
        └── YYYY-MM-DD-topic.md  # End-of-session summaries
```

The canonical template lives in `hermes-core/templates/project/`. If Villa has the core repo locally, the quickest bootstrap is:

```bash
"<path-to>/hermes-core/scripts/new-project-memory.sh" /path/to/repo
```

It never overwrites existing files.

## Existing CLAUDE.md

Hermes loads one context file per session (`.hermes.md` → `AGENTS.md` → `CLAUDE.md`). If the repo already has a `CLAUDE.md`, do not create `AGENTS.md`: keep `CLAUDE.md` as the entry point and add a short pointer to `docs/agent/` in it.

## Bootstrapping a repo without the script

1. Read the repo first: README, package manifests (`composer.json`, `package.json`), docker files, CI config, folder structure.
2. Create the layout above. Fill `AGENTS.md` and `context.md` with **facts you verified** in the code. Mark guesses with `TODO(confirm):`.
3. Show Villa the result and ask him to confirm the TODOs before committing.
4. Commit as: `docs: add agent project memory`.

## Recording a decision (ADR)

1. Find the next number: highest `NNNN` in `docs/agent/decisions/` + 1.
2. Copy `0000-template.md` to `NNNN-kebab-title.md` and fill it: context, decision, alternatives considered, consequences.
3. Status is `Accepted` only if Villa agreed; otherwise `Proposed`.
4. Include the ADR in the same commit as the change it explains when possible.

## Adding a gotcha

Add one bullet at the top of `gotchas.md`: `- **<short title>** — what happens, why, and how to avoid it. (YYYY-MM-DD)`

## Rules

- English only.
- Never store secrets, credentials or customer personal data in these files.
- Keep `AGENTS.md` short (under ~150 lines); push detail into `context.md`.
- Update stale facts instead of appending contradictions.
