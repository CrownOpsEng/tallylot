# File Map

Use this file when you know the task and want the smallest relevant doc,
command, artifact, or agent route.

## Task Routing

| If you need to... | Use this |
| ---- | ---- |
| understand the current implemented surface | `docs/operations/project-state.md` |
| make a code or architecture change | `docs/architecture/engineering-standards.md` |
| follow repo coding discipline while implementing | `docs/architecture/implementation-working-agreement.md` |
| work on reconciliation, checkpoints, journaling, or tax | `docs/architecture/reconciliation-tax-implementation-plan.md` |
| enforce platform-agnostic runtime and oracle boundaries | `docs/architecture/oracle-and-input-boundaries.md` |
| map transaction semantics and support tiers | `docs/architecture/transaction-classification-matrix.md` |
| follow the no-big-bang migration order | `docs/architecture/implementation-migration-sequence.md` |
| author or repair a source or output adapter | `docs/architecture/adapter-authoring.md` |
| follow the short operator workflow | `docs/operations/operations-quickstart.md` |
| follow the detailed operator workflow | `docs/operations/mop.md` |
| review baseline artifact expectations | `docs/operations/baseline-validation.md` |
| review wallet inventory outputs | `docs/operations/wallet-inventory.md` |
| review timezone provenance outputs | `docs/operations/timezone-validation.md` |
| check export and verification hygiene | `docs/operations/export-checklist.md` |
| check commit format and checkpoint rules | `docs/architecture/commit-standards.md` |
| load a compact repo-specific agent prompt | `docs/operations/ai-session-prompt.md` |
| inspect supported CoinTracking oracle artifact families | `docs/reference/cointracking-oracle-artifacts.md` |

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
