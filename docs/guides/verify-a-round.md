---
title: "Verify A Round"
summary: "Detailed procedure for scaffolding, exporting, comparing, and closing a verification round."
doc_type: guide
audience: human
owner: repo
status: active
nav_order: 40
---

Use this guide after a candidate is ready for a manual repair or import round
in the external verification tool.

## Seed The Round

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli round scaffold \
  --round-id <round_id> \
  --phase <phase> \
  --source <source>
```

## Execute The Manual Step

1. Make the manual repair or import in the external verification tool.
2. Save the fresh verification export set under
   `working/verification/<round_id>/`.
3. Use [Export Checklist](../reference/export-checklist.md) for the exact
   export set.

## Compare The Round

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli verification compare \
  --previous-dir <prior_verification_dir> \
  --current-dir <workspace>/working/verification/<round_id> \
  --output-dir <workspace>/working/verification/<round_id>/comparison
```

Review the comparison package before moving on.

## Close The Round

Update:

- `analysis/issues/issue_log.csv`
- `analysis/issues/source_inventory.csv` when the round touched a source
- `outputs/logs/round_log.csv`

Do not advance to the next source until the current round is verified.
