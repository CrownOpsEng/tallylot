# Workspace Layout

The application operates against an external workspace rooted outside the repo.
The workspace is seeded by `workspace init`.

## Layout

```text
workspace/
  analysis/
    inventory/
    issues/
    reconciliation/
  config/
  docs/
  evidence/
    raw/
      portfolio/
      source/
  outputs/
    checkpoints/
    logs/
    reports/
  working/
    import_batches/
    normalized/
    supporting_artifacts/
    verification/
```

## Seeded Control Files

- `analysis/issues/issue_log.csv`
- `analysis/issues/source_inventory.csv`
- `analysis/inventory/wallet_inventory.csv`
- `outputs/logs/round_log.csv`
- `config/workspace.json`

## Design Notes

- Evidence remains file-based even if canonical records move into SQLite later.
- The application writes deterministic CSV and JSON artifacts into the
  workspace.
- The repo should never require users to place their documents inside the git
  checkout.
