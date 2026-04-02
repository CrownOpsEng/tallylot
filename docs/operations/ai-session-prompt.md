# AI Session Working Prompt

Use this repo as the typed evidence, reconciliation, checkpoint, accounting,
and tax-computation toolchain.

Start with these facts:

1. Historical baseline folder:
   `evidence/raw/portfolio/cointracking/2023-08-05_full_export/`
2. Authoritative cutoff timestamp: `2023-08-05 08:34:04`
3. Delta work begins strictly after that timestamp unless a new baseline is
   intentionally adopted
4. `2023-08-05` is a historical oracle boundary, not a balance-confirmed
   checkpoint
5. The first hard checkpoint target is the best-evidenced balance date around
   `2026-03-23`
6. The implementation anchor is
   `docs/architecture/reconciliation-tax-implementation-plan.md`
7. The only implemented file output adapter today is `cointracking_csv`
8. CoinTracking tax and accounting reports stay in comparison tooling; they are
   not runtime inputs
9. Follow `docs/architecture/implementation-working-agreement.md` for execution
   discipline

Check these artifacts first:

1. baseline validation package under `analysis/reconciliation/`
2. `analysis/issues/issue_log.csv`
3. `analysis/issues/source_inventory.csv`
4. `working/verification/`
5. `working/normalized/`
6. `working/import_batches/`
7. raw captures under `evidence/raw/source/`

Working rules:

1. Prefer the typed CLI commands over manual file shaping.
2. Stop before staging or importing when `timezone_issues.csv`,
   `exceptions.csv`, or `stage_summary.json` still show blockers.
3. Update the round log after each seeded round and verification cycle.
4. Use `uv run python -m tools.oracles.cli source diff` when a candidate or
   reference slice needs a deterministic row comparison.
5. Build reconciliation before tax computation.
6. Keep the core centered on provider-neutral transaction facts.
7. Keep journaling behind a renderer port and tax behavior behind a policy
   port.
8. Keep `pydantic` at repo boundaries, not in the core domain.
9. Surface unsupported or ambiguous facts as issues.
10. Refactor obvious shared seams instead of duplicating logic.
11. Add or update tests with new behavior.
12. Make stable checkpoint commits without waiting for reminders.
