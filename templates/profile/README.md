# hermes-__NAME__

Hermes Agent profile distribution: __DESCRIPTION__

This repo holds the agent's **rules, config and skills** — never credentials or memory.

| File | Purpose | Edit? |
|------|---------|-------|
| `SOUL.local.md` | Profile-specific identity and rules | Yes |
| `SOUL.md` | Generated: `hermes-core/SOUL.base.md` + `SOUL.local.md` | No — run `../hermes-core/scripts/build.sh` |
| `config.yaml` | Model, working directory, MCP (Composio) | Yes |
| `distribution.yaml` | Distribution manifest | Bump `version` on changes |
| `skills/core/` | Generated copy of the shared core skills | No |
| `skills/<other>/` | Skills specific to this profile | Yes |

## Install / update

```bash
../hermes-core/scripts/install.sh __NAME__
cp ~/.hermes/profiles/__NAME__/.env.EXAMPLE ~/.hermes/profiles/__NAME__/.env   # first time; add COMPOSIO_API_KEY
__NAME__ chat
```

See `hermes-core/README.md` for the full workflow.
