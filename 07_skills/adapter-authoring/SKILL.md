---
name: adapter-authoring
description: Use when creating or extending a source adapter, repairing adapter logic, or documenting the normalization contract for new sources, especially around grouped trades, transfers, margin activity, and fee handling.
---

# Adapter Authoring

Use this skill when the task is adapter implementation, not operational intake.

## Default workflow

1. Run `06_scripts/profile_source.py` first and work from `profile.json` plus `profile_inventory.csv`, not from ad-hoc guesses.
2. Implement source logic inside `06_scripts/source_adapters.py`.
3. Reuse shared helpers before adding source-specific branching:
   - `06_scripts/pipeline_common.py` for profile/schema helpers
   - `06_scripts/normalization_common.py` for canonical fee attachment
   - `06_scripts/render_cointracking.py` for output shaping
4. Emit canonical events that preserve the economic event count as much as possible.
5. Add or update deterministic tests:
   - unit test for the adapter path
   - e2e normalization coverage when CLI behavior changes
6. Re-run normalization and confirm the new rows land in either:
   - canonical outputs
   - explicit `exceptions.csv`

## Normalization rules

- Canonical normalization is source-agnostic. Adapters should describe source rows in the shared canonical schema, not in CoinTracking-specific terms unless a render field needs it.
- Keep one economic action in one canonical event whenever the source supports it.
- Keep the associated fee on the same canonical trade, deposit, withdrawal, staking, or unstaking event when that fee is part of the same source action.
- Only emit a standalone fee event when the source truly exposes a fee-only action with no principal movement to attach it to.
- Internal transfers, staking shuffles, and wallet/account movements should stay explicit in canonical events rather than being silently dropped.
- Margin, funding, borrow, repayment, liquidation, and rebate rows must never be silently ignored. Normalize them or surface them in `exceptions.csv`.
- If the source cannot justify a safe mapping, prefer an explicit exception over a guessed transaction.

## Output rules

- CoinTracking is currently the only output adapter.
- Keep canonical normalization richer than the CoinTracking render when needed.
- If CoinTracking eventually needs a split representation, do that in rendering or a future output adapter, not by degrading canonical normalization.

## Guardrails

- Never patch around a source bug by editing raw exports.
- Never hide unsupported rows by adding them to an ignore list without an explicit review path.
- Never merge rows across timestamps or accounts unless the source evidence makes that grouping deterministic.
- Prefer compact fixtures over full raw dumps in tests and repair loops.
