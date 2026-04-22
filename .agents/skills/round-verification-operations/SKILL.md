---
name: round-verification-operations
description: >-
  Run tallylot's oracle screening, staging, and round verification path with
  the documented repo workflow. Use when the task is candidate screening,
  staging, round scaffolding, export comparison, or round close-out.
---

# Round Verification Operations

Use this skill for round verification workflow execution.

## Workflow

1. Read the verification route first:
   - `docs/guides/normalize-screen-stage.md`
   - `docs/guides/verify-a-round.md`
   - `docs/guides/full-operator-workflow.md`
   - `.claude/commands/round-verification.md`
2. Use the documented oracle CLI commands:
   - `make oracle ARGS='batch screen'`
   - `make oracle ARGS='batch stage'`
   - `make oracle ARGS='round scaffold'`
   - `make oracle ARGS='verification compare'`
3. Use `make oracle ARGS='source diff'` when the candidate or reference slice
   needs deterministic source-level repair context before import or compare.
4. Review the screen, stage, round, and comparison artifacts before answering
   final review questions.

## Focus

- keep oracle work dev-only
- use explicit exported artifacts for review
- do not treat oracle outputs as runtime state
