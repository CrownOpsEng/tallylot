---
name: round-verification-operations
description: >-
  Run tallylot's round verification and oracle comparison path with the
  documented repo workflow. Use when the task is scaffolding, exporting,
  comparing, or closing a verification round.
---

# Round Verification Operations

Use this skill for round verification workflow execution.

## Workflow

1. Read the verification route first:
   - `docs/guides/verify-a-round.md`
   - `docs/guides/full-operator-workflow.md`
   - `.claude/commands/round-verification.md`
2. Use the documented oracle CLI commands:
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli round scaffold`
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli verification compare`
3. Review the round artifacts and comparison outputs before answering closeout
   questions.
4. Use `source diff` only when the verification path needs source-level repair
   context.

## Focus

- keep oracle work dev-only
- use explicit exported artifacts for review
- do not treat oracle outputs as runtime state
