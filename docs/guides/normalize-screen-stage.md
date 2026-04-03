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
