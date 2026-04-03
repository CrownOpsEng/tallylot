# AI Session Working Prompt

Use this repo as the typed evidence, reconciliation, checkpoint, accounting,
and tax-computation toolchain. Treat CoinTracking as a compatibility and
historical oracle layer, not as the live ledger target for new architecture
work.

Anchor to these facts first:

1. Canonical baseline folder:
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
7. CoinTracking tax and accounting reports are oracle-only support artifacts,
   not normal runtime inputs
8. follow `docs/architecture/implementation-working-agreement.md` for execution discipline

Priority artifacts:

1. baseline validation package under `analysis/reconciliation/`
2. `analysis/issues/issue_log.csv`
3. `analysis/issues/source_inventory.csv`
4. `working/verification/`
5. `working/normalized/`
6. `working/import_batches/`
7. raw captures under `evidence/raw/source/`

Operational rules:

1. prefer the typed CLI commands over manual file shaping
2. do not stage or import a source while `timezone_issues.csv`, `exceptions.csv`,
   or `stage_summary.json` show unresolved blockers
3. update the round log after each seeded round and verification cycle
4. use `source reconcile` when a candidate or reference slice needs a
   deterministic row comparison
5. for new architecture work, build reconciliation before tax computation
6. keep the system centered on provider-neutral transaction facts, not the
   current canonical event shape
7. keep journaling behind a renderer port and tax behavior behind a policy port
8. expand `pydantic` only at repo boundaries, not through the core domain
9. do not silently suppress unsupported or ambiguous facts; log them as issues
10. refactor obvious shared seams instead of duplicating logic in place
11. create or update tests alongside new behavior and structure
12. make stable checkpoint commits without waiting for user reminders
13. keep normal runtime workflows reconstructable from source evidence and
    intentional checkpoints without requiring CoinTracking tax outputs
