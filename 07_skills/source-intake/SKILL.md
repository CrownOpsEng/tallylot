---
name: source-intake
description: Use when capturing or reviewing a new exchange or wallet source for this repo, especially when deciding raw evidence completeness, manifesting, profiling, adapter selection, and whether a source is importable, evidence-only, or blocked.
---

# Source Intake

Use this skill for the deterministic front half of source prep.

## Default workflow

1. Confirm the source row in `03_analysis/issues/source_inventory.csv`.
2. Capture untouched exports in `01_raw_exports/external/<source>/raw/`.
3. Run `06_scripts/source_manifest.py`.
4. Run `06_scripts/profile_source.py`.
5. Review `profile.json` and `profile_inventory.csv`.
6. Update `source_inventory.csv` with:
   - `profile_status`
   - `adapter`
   - `normalization_status`
   - `candidate_path` when known
7. Decide one of three outcomes:
   - importable
   - evidence_only
   - blocked

## Decision rules

- Prefer deterministic evidence over interpretation.
- Do not send full raw exports to an LLM when profile artifacts are enough.
- If file families are unknown or the adapter is unsupported, mark normalization as pending and route to the normalization-exceptions skill only after profiling is complete.
- If normalization is `ready`, that still means "candidate staged for human review", not "safe to import without checking overlap and verification gates".
- If normalization is `needs_review`, prefer a compact exception artifact and an issue-log entry over hand-editing raw exports or silently dropping ambiguous rows.
- Keep the raw folder immutable.

## Commands

```bash
python3 06_scripts/source_manifest.py \
  --source-dir 01_raw_exports/external/<source>/raw \
  --output 01_raw_exports/external/<source>/manifest.csv
```

```bash
python3 06_scripts/profile_source.py \
  --source "<Source Name>" \
  --raw-dir 01_raw_exports/external/<source>/raw \
  --out-dir 02_working/normalized/<source>
```
