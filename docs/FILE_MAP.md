# File Map

Use this file when you need the smallest relevant artifact, command, or
repo-local agent entrypoint.

## Primary Docs

| File | Purpose |
| ---- | ------- |
| `docs/MOP.md` | Full typed-package workflow and manual CoinTracking procedure |
| `docs/OPERATIONS_QUICKSTART.md` | Shortest safe route through the workflow |
| `docs/BASELINE_VALIDATION.md` | Baseline validation artifact package |
| `docs/WALLET_INVENTORY.md` | Wallet inventory rebuild outputs and review rules |
| `docs/TIMEZONE_VALIDATION.md` | Timezone provenance and review contract |
| `docs/EXPORT_CHECKLIST.md` | Verification export and staging checklist |
| `docs/PROJECT_STATE.md` | Current implemented runtime surface |
| `docs/AI_SESSION_PROMPT.md` | Compact agent context |

## Active Workspace Artifacts

| Path | Purpose |
| ---- | ------- |
| `analysis/issues/issue_log.csv` | Master issue register |
| `analysis/issues/source_inventory.csv` | Source queue and status tracker |
| `analysis/inventory/wallet_inventory.csv` | Canonical wallet inventory |
| `analysis/inventory/wallet_inventory_evidence.csv` | Evidence rows for wallet identifiers |
| `analysis/inventory/wallet_inventory_issues.csv` | Deterministic wallet review issues |
| `analysis/inventory/wallet_inventory_summary.json` | Wallet inventory counts |
| `analysis/reconciliation/` | Baseline validation outputs |
| `outputs/logs/round_log.csv` | Round log seeded by `round scaffold` |
| `working/normalized/<source>/` | Profile, normalization, timezone, and candidate artifacts |
| `working/import_batches/<source>/` | Batch screening and staged import artifacts |
| `working/verification/<round_id>/` | Fresh post-action CoinTracking exports |

## Typed Commands

| Command | Purpose |
| ---- | ------- |
| `workspace init` | Seed the external workspace |
| `source manifest` | Build a deterministic capture manifest |
| `source profile` | Build file inventory plus timezone provenance |
| `source normalize` | Produce canonical outputs and a CoinTracking candidate |
| `wallet inventory rebuild` | Aggregate wallet inventory artifacts |
| `baseline validate` | Produce the full baseline reconciliation package |
| `batch screen` | Validate and screen a candidate without copying it |
| `batch stage` | Screen and copy a passing candidate |
| `verification compare` | Compare two verification export sets |
| `round scaffold` | Create a round folder and seed the round log |
| `source reconcile` | Compare candidate and reference ledger slices |
| `supporting extract-pdf-balances` | Extract balances from supported PDF statements |

## Repo-Local Agent Entry Points

| Path | Purpose |
| ---- | ------- |
| `.claude/commands/source-intake.md` | Profile, normalize, screen, and stage a source |
| `.claude/commands/round-verification.md` | Verification compare and round-close workflow |
| `.claude/commands/wallet-inventory.md` | Wallet inventory rebuild workflow |
| `.claude/commands/normalization-exceptions.md` | Review normalization exceptions and reviews |
| `.claude/commands/adapter-authoring.md` | Adapter authoring and repair route |
