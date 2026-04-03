---
name: normalization-exceptions
description: Use when canonical normalization leaves rows in exceptions.csv, when an adapter no longer matches source format, or when the AI should draft a durable adapter repair instead of repeating ad-hoc row handling.
---

# Normalization Exceptions

Use this skill only after deterministic profiling and normalization have run.

## Inputs

- `02_working/normalized/<source>/profile.json`
- `02_working/normalized/<source>/exceptions.csv`
- `02_working/normalized/<source>/normalization_summary.json`
- the raw manifest fingerprint from the profile

## Default workflow

1. Classify the failure:
   - data exception
   - schema drift
   - adapter bug
2. If it is a data exception, prepare a compact decision artifact keyed by:
   - `manifest_fingerprint`
   - `event_id`
3. If it is an adapter bug, draft a durable repair:
   - minimal fixture
   - adapter patch
   - regression test
4. Re-run normalization after the patch.
5. If a source still has a small unresolved set after the durable repair, log the residual items and keep them explicit rather than forcing the adapter to guess.

## Guardrails

- Never rewrite adapters silently from full raw exports.
- Use compact fixture slices, not entire ledgers, for repair prompts.
- Only propose adapter promotion after deterministic tests pass.
- Keep ledger-impacting issues in `03_analysis/issues/issue_log.csv`; parser noise stays out unless it blocks import or verification.
- When an exception becomes an issue-log row, use the allowed append-only prefix families and assign the next `max(existing) + 1` number within that family. If the result is a balance mismatch with unknown origin, use `BAL-*`; do not renumber old rows or invent source-specific namespaces.
- "Universal" means deterministic coverage plus visible review gates, not automatic treatment of every exchange-specific internal movement.

## Decision memory

Persist accepted row-level decisions in `exception_decisions.csv` beside the normalized outputs.
Do not re-send the same `event_id` to the LLM when the manifest fingerprint has not changed.
