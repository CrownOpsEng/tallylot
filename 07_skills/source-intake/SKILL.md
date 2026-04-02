---
name: source-intake
description: Use when capturing or reviewing a new exchange or wallet source for this repo, especially when deciding raw evidence completeness, manifesting, profiling, adapter selection, and whether a source is importable, evidence-only, or blocked.
---

# Source Intake

Use this skill for the deterministic front half of source prep.

## Default workflow

1. If the evidence starts as a mixed dump, run `06_scripts/intake_sort.py` in dry-run mode first.
2. Review any `review_required` files and historical-date routing decisions in the intake report.
3. Apply `06_scripts/intake_sort.py` only after the dry-run report is acceptable.
4. Confirm the source row in `03_analysis/issues/source_inventory.csv`.
5. Run `06_scripts/source_manifest.py` against the canonical capture folder.
6. Run `06_scripts/profile_source.py`.
7. Review `profile.json` and `profile_inventory.csv`.
8. Update `source_inventory.csv` with:
   - `profile_status`
   - `adapter`
   - `normalization_status`
   - `candidate_path` when known
9. Decide one of three outcomes:
   - importable
   - evidence_only
   - blocked
10. If the source needs an issue-log row, append it to `03_analysis/issues/issue_log.csv` using the allowed prefix families and the next `max(existing) + 1` number for that family. Use `BAL-*` for balance gaps whose origin is not yet proven; do not invent exchange-specific prefixes or reuse skipped numbers.

## Decision rules

- Prefer deterministic evidence over interpretation.
- Do not send full raw exports to an LLM when profile artifacts are enough.
- Intake is immutable placement only: never edit, dedupe, or suppress raw files during sorting.
- Historical capture IDs must come from defensible historical evidence, never from the arrival date of the dump.
- If file families are unknown or the adapter is unsupported, mark normalization as pending and route to `07_skills/adapter-authoring/` after profiling is complete.
- If normalization is `ready`, that still means "candidate staged for human review", not "safe to import without checking overlap and verification gates".
- If normalization is `needs_review`, prefer a compact exception artifact and an issue-log entry over hand-editing raw exports or silently dropping ambiguous rows.
- Keep the capture folder immutable.

## Commands

```bash
python3 06_scripts/intake_sort.py \
  --incoming-dir 01_raw_exports/incoming \
  --report-dir 02_working/intake_reports/<batch_id>
```

```bash
python3 06_scripts/intake_sort.py \
  --incoming-dir 01_raw_exports/incoming \
  --report-dir 02_working/intake_reports/<batch_id> \
  --apply
```

```bash
python3 06_scripts/source_manifest.py \
  --source-dir 01_raw_exports/external/<source>/<capture_id> \
  --output 01_raw_exports/external/<source>/<capture_id>/manifest.csv
```

```bash
python3 06_scripts/profile_source.py \
  --source "<Source Name>" \
  --raw-dir 01_raw_exports/external/<source>/<capture_id> \
  --out-dir 02_working/normalized/<source>
```
