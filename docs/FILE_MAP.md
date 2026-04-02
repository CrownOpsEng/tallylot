# File Map

Use this file when you know the task and want the smallest relevant doc,
command, artifact, or agent route.

## Task Routing

| If you need to... | Use this |
| ---- | ---- |
| understand the current implemented surface | `docs/PROJECT_STATE.md` |
| make a code or architecture change | `docs/engineering-standards.md` |
| follow repo coding discipline while implementing | `docs/IMPLEMENTATION_WORKING_AGREEMENT.md` |
| work on reconciliation, checkpoints, journaling, or tax | `docs/RECONCILIATION_TAX_IMPLEMENTATION_PLAN.md` |
| enforce platform-agnostic runtime and oracle boundaries | `docs/ORACLE_AND_INPUT_BOUNDARIES.md` |
| map transaction semantics and support tiers | `docs/TRANSACTION_CLASSIFICATION_MATRIX.md` |
| follow the no-big-bang migration order | `docs/IMPLEMENTATION_MIGRATION_SEQUENCE.md` |
| author or repair a source or output adapter | `docs/adapter-authoring.md` |
| follow the short operator workflow | `docs/OPERATIONS_QUICKSTART.md` |
| follow the detailed operator workflow | `docs/MOP.md` |
| review baseline artifact expectations | `docs/BASELINE_VALIDATION.md` |
| review wallet inventory outputs | `docs/WALLET_INVENTORY.md` |
| review timezone provenance outputs | `docs/TIMEZONE_VALIDATION.md` |
| check export and verification hygiene | `docs/EXPORT_CHECKLIST.md` |
| check commit format and checkpoint rules | `docs/commit-standards.md` |
| load a compact repo-specific agent prompt | `docs/AI_SESSION_PROMPT.md` |

## Workspace Artifacts

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
| `working/supporting_artifacts/intake/<capture>/` | Intake-copied supporting artifacts for a capture |
| `working/verification/<round_id>/` | Fresh post-action verification exports |

## Typed Commands

| Command | Purpose |
| ---- | ------- |
| `workspace init` | Seed the external workspace |
| `source intake plan` | Build an archive-aware intake plan and issue report |
| `source intake apply` | Copy loose evidence into workspace capture paths and write intake reports |
| `source manifest` | Build a deterministic capture manifest |
| `source profile` | Build file inventory plus timezone provenance |
| `source normalize` | Produce canonical outputs and a CoinTracking candidate |
| `batch screen` | Validate and screen a candidate without copying it |
| `batch stage` | Screen and copy a passing candidate |
| `baseline validate` | Produce the full baseline reconciliation package |
| `verification compare` | Compare two verification export sets |
| `round scaffold` | Create a round folder and seed the round log |
| `source reconcile` | Compare candidate and reference ledger slices |
| `wallet inventory rebuild` | Aggregate wallet inventory artifacts |
| `supporting extract-pdf-balances` | Extract balances from supported PDF statements |

## Repo Tools

| Command | Purpose |
| ---- | ------- |
| `uv run python -m tools.scaffold_adapter ...` | Seed a package-style adapter with colocated tests and fixtures |
| `uv run python -m tools.refresh_adapter_goldens ...` | Refresh adapter-pack JSON goldens through the typed services |

## Agent Routes

| Path | Purpose |
| ---- | ------- |
| `.claude/commands/source-intake.md` | Profile, normalize, screen, stage, and reconcile a source |
| `.claude/commands/round-verification.md` | Verification compare and round-close workflow |
| `.claude/commands/wallet-inventory.md` | Wallet inventory rebuild workflow |
| `.claude/commands/normalization-exceptions.md` | Review normalization exceptions and reviews |
| `.claude/commands/source-reconcile.md` | Candidate-versus-reference reconciliation workflow |
| `.claude/commands/reconciliation-tax-build.md` | Architecture and implementation route for reconciliation, checkpointing, accounting, and tax |
| `.claude/commands/implementation-checkpoint.md` | Final implementation review, verification, and commit route |
| `.claude/commands/supporting-artifacts.md` | PDF balance extraction and supporting evidence workflow |
| `.claude/commands/adapter-authoring.md` | Adapter authoring and repair route |
