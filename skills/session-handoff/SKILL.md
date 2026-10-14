---
name: session-handoff
description: Write an end-of-session handoff into docs/agent/handoffs/ so the next session (or another agent) can resume — use when wrapping up substantial work in a repo or when Villa says he is stopping.
version: 1.0.0
metadata:
  hermes:
    tags: [memory, handoff]
    category: core
---

# Session handoff

## When

- Villa says he is done for now, switching projects, or "dejémoslo aquí".
- A long task is paused midway.
- Before a context-heavy session ends.

## Steps

1. Run `git status` and `git log --oneline -15` to see what actually changed.
2. Create `docs/agent/handoffs/YYYY-MM-DD-<topic>.md` (create the folder if missing) with:

```markdown
# Handoff — <topic> (YYYY-MM-DD)

## Goal
What we were trying to achieve.

## Done
- Concrete changes, with commit hashes or file paths.

## In progress / not finished
- What is half-done and its current state.

## Next steps
1. Ordered, actionable steps.

## Open questions
- Things that need Villa's decision.

## Notes
- Commands, env quirks, links worth keeping.
```

3. If a decision was made during the session and has no ADR yet, create it (see `project-memory`).
4. If you learned a trap, add it to `gotchas.md`.
5. Ask Villa whether to commit the handoff (`docs: add handoff <topic>`). Do not push.

## Rules

- English, factual, short. No secrets.
- Reference files and commits, do not paste large code blocks.
