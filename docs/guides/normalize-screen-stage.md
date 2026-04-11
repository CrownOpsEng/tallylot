---
title: "Normalize, Screen, And Stage"
summary: "Detailed procedure for normalization review, candidate rendering, oracle screening, and staging."
doc_type: guide
audience: human
owner: repo
status: active
nav_order: 30
---

Use this guide when a settled source capture is ready for normalization and
round preparation.

## Normalize The Capture

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source normalize \
  --source <source> \
  --raw-dir <workspace>/evidence/raw/source/<source>/<capture_label>
```

`source normalize` requires the exact materialized capture root under
`evidence/raw/source/<source>/<capture_label>/`. The command rejects source
roots, arbitrary directories, and any root whose `capture.json` metadata does
not match the path and requested source.

When the raw capture lives inside the workspace, the default output root stays
`working/normalized/captures/<capture_uid>/`.

Review:

- `facts.csv`
- `fact_annotations.json`
- `balance_snapshots.csv`
- `balance_references.csv`
- `exceptions.csv`
- `normalization_reviews.csv`
- `location_inventory.csv`
- `normalization_summary.json`

`checkpoint extract-pdf-balances` uses the same statement extraction path as
normalization. Use it when you need the standalone statement parser output for
the same supported PDF families.

`balance_references.csv` is the unified reference artifact. Normalization
contributes `source_document` rows when the capture actually contains usable
balance evidence. `exceptions.csv` and `normalization_reviews.csv` keep
`raw_row_ref` plus the same locator family with `raw_` prefixes when they
reference raw evidence.

## Assemble The Source Dataset

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source assemble \
  --source <source> \
  --workspace-root <workspace>
```

Review the assembled source dataset under
`<workspace>/working/normalized/sources/<source>/`.

`source assemble` is rerun-safe. It rewrites only its known generated files
such as `facts.csv`, `balance_snapshots.csv`, `balance_references.csv`,
`assembly_summary.json`, and `assembly_issues.csv`, and leaves unrelated
operator-owned files in place.

## Submit Manual Balances When Needed

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot checkpoint scaffold-balance-submission \
  --source <source>
```

Fill the submission package under
`<workspace>/working/supporting_artifacts/balance_submissions/<source>/`, then
run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot checkpoint submit-balances \
  --source <source>
```

Review:

- `balance_submission_summary.json`
- `balance_submission_issues.csv` when the submit run reports issues

Use this path when normalization did not already emit balance outputs or when
the source's balance facts need to be entered through a validated manual
package. By default, the submit workflow materializes `balance_snapshots.csv`,
`balance_references.csv`, and optional `location_inventory.csv` under
`<workspace>/working/normalized/sources/<source>/`.

Optional `location_inventory.csv` improves later cross-source corroboration,
but source-local balance checks still work without it.

## Check Source Balances

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot reconciliation balances check \
  --input-root <workspace>/working/normalized/sources \
  --output-root <workspace>/analysis/reconciliation/<source>
```

`<workspace>/working/normalized/sources/` is the assembled reconciliation
input root. Each source subdirectory may contain source-backed evidence from
normalization, operator-confirmed balance references from
`checkpoint submit-balances`, or both.

Review:

- `balance_check_summary.csv`
- `balance_assertions.csv`
- `reconciliation_issues.csv`
- `balance_reconciliation_summary.json`
- `cross_source_assertions.csv`
- `cross_source_issues.csv`
- `cross_source_summary.json`

Continue only after reviewing any emitted reconciliation issues.

## Render A Candidate When Needed

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot output render file \
  --output-adapter cointracking_csv \
  --facts <workspace>/working/normalized/sources/<source>/facts.csv \
  --output <workspace>/working/normalized/sources/<source>/cointracking_candidate.csv
```

Render a candidate only when the round needs an external output artifact such
as `cointracking_candidate.csv`.

## Screen The Candidate

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli batch screen \
  --candidate <workspace>/working/normalized/sources/<source>/cointracking_candidate.csv \
  --baseline-export-dir <workspace>/evidence/raw/portfolio/cointracking/2023-08-05_full_export \
  --output-dir <workspace>/working/import_batches/<source>
```

Review:

- `stage_issues.csv`
- `stage_summary.json`

Stop when `stage_summary.json` reports `passed: false`.

## Stage The Candidate

Run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli batch stage`
only after the candidate passes the screen.

## Diff When Needed

Run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli source diff`
when the candidate or reference slice needs a deterministic row comparison
before import.

Use [Verify A Round](verify-a-round.md) after the candidate has passed the
screen and the round is ready for manual execution.
