# Portfolio Exports

Store portfolio-system exports and tracker captures here. The current
historical baseline and most saved bundles happen to live under the
`cointracking/` subtree.

This branch is separate from `evidence/raw/source/` on purpose:

- `source/` holds upstream evidence from exchanges, wallets, explorers, bots, and other external systems
- `portfolio/` holds portfolio-tracker exports, saved report bundles, and
  other portfolio-system outputs used for baseline locking, verification, and
  reconciliation

Rules:

- never treat portfolio exports as raw source truth
- keep the historical baseline oracle bundle in `evidence/raw/portfolio/cointracking/2023-08-05_full_export/`
- place later CoinTracking export captures under `evidence/raw/portfolio/cointracking/history/<capture_id>/`
- keep saved HTML exports with their sidecar bundles together inside the same capture
