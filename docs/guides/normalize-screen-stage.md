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
  --raw-dir <workspace>/evidence/raw/source/<source>/<capture_id> \
  --output-dir <workspace>/working/normalized/<source>
```

Review:

- `facts.csv`
- `fact_annotations.json`
- `balances.csv`
- `balance_evidence.csv`
- `exceptions.csv`
- `normalization_reviews.csv`
- `normalization_summary.json`

If normalization already produced canonical `balances.csv` and
`balance_evidence.csv`, use them directly in the balance check flow below.

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
- `balance_submission_issues.csv`

Use this path when normalization did not already emit canonical balance
artifacts or when the source's balance facts need to be entered through a
validated manual package. By default, the submit workflow materializes the
canonical outputs under `<workspace>/working/normalized/<source>/`.

Optional `location_inventory.csv` improves later cross-source corroboration,
but source-local balance checks still work without it.

## Check Source Balances

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot reconciliation balances check \
  --input-root <workspace>/working/normalized/<source> \
  --output-root <workspace>/analysis/reconciliation/<source>
```

`<workspace>/working/normalized/<source>/` may come directly from
normalization or from `checkpoint submit-balances`.

Review:

- `balance_check_summary.csv`
- `balance_assertions.csv`
- `reconciliation_issues.csv`
- `balance_assertion_summary.json`
- `cross_source_assertions.csv`
- `cross_source_issues.csv`
- `cross_source_summary.json`

Continue only after reviewing any emitted reconciliation issues.

## Render A Candidate When Needed

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot output render file \
  --output-adapter cointracking_csv \
  --facts <workspace>/working/normalized/<source>/facts.csv \
  --output <workspace>/working/normalized/<source>/cointracking_candidate.csv
```

Render a candidate only when the round needs an external output artifact such
as `cointracking_candidate.csv`.

## Screen The Candidate

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli batch screen \
  --candidate <workspace>/working/normalized/<source>/cointracking_candidate.csv \
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
