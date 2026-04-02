# Workspace Layout

The application operates against an external workspace rooted outside the repo.
The workspace is seeded by `workspace init`.

## Layout

```text
workspace/
  analysis/
    checklists/
    inventory/
    issues/
    reconciliation/
  config/
  docs/
  evidence/
    raw/
      incoming/  # historical migration quarantine; not seeded for new intake
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
- Repo-owned workspace subtree guidance and templates live under
  `docs/workspace/`.
- Workspace docs under the external root are live operator copies, not the
  version-controlled source of truth.
- Repo operational docs and live artifacts were migrated out of the checkout on
  2026-03-26 with this mapping:
  - `00_docs/` -> `docs/`
  - `01_raw_exports/source/` -> `evidence/raw/source/`
  - `01_raw_exports/portfolio/` -> `evidence/raw/portfolio/`
  - `01_raw_exports/incoming/` -> `evidence/raw/incoming/`
  - `02_working/` -> `working/`
  - `03_analysis/` -> `analysis/`
  - `05_outputs/` -> `outputs/`
- The legacy `04_import_ready/` root is retired. Approved staged imports remain
  under `working/import_batches/`.
