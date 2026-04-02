# File Map

Use this file when you know the task and want the smallest relevant doc,
command, artifact, or agent route.

## Task Routing

| If you need to... | Use this |
| ---- | ---- |
| plan the remaining work | `ROADMAP.md` |
| review completed milestones | `CHANGELOG.md` |
| understand the current implemented surface | `docs/status/current-state.md` |
| understand doc ownership and routing | `docs/README.md` |
| make a code or architecture change | `docs/standards/engineering.md` |
| follow repo coding discipline while implementing | `docs/standards/implementation.md` |
| work on reconciliation, checkpoints, journaling, or tax | `docs/concepts/reconciliation-tax-architecture.md` |
| enforce platform-agnostic runtime and oracle boundaries | `docs/concepts/oracle-boundaries.md` |
| map transaction semantics and support tiers | `docs/concepts/transaction-classification.md` |
| follow the no-big-bang migration order | `docs/status/migration-sequence.md` |
| author or repair a source or output adapter | `docs/guides/write-an-adapter.md` |
| follow the short operator workflow | `docs/guides/operator-quickstart.md` |
| follow the detailed operator workflow | `docs/guides/full-operator-workflow.md` |
| understand external workspace layout | `docs/concepts/workspace-model.md` |
| understand repo-owned workspace guides | `docs/workspace/README.md` |
| review baseline artifact expectations | `docs/reference/baseline-validation-contract.md` |
| review location inventory outputs | `docs/reference/wallet-inventory-artifacts.md` |
| review timezone provenance outputs | `docs/reference/timezone-validation-artifacts.md` |
| check export and verification hygiene | `docs/reference/export-checklist.md` |
| check commit format and checkpoint rules | `docs/standards/commits.md` |
| load a compact repo-specific agent prompt | `docs/operations/ai-session-prompt.md` |
| inspect supported historical oracle artifact families | `docs/reference/cointracking-oracle-artifacts.md` |

## Workspace Artifacts

| Path | Purpose |
| ---- | ------- |
| `analysis/issues/issue_log.csv` | Master issue register |
| `analysis/issues/source_inventory.csv` | Source queue and status tracker |
| `analysis/inventory/location_inventory.csv` | Normalized location inventory |
| `analysis/inventory/location_inventory_evidence.csv` | Evidence rows for wallet identifiers |
| `analysis/inventory/location_inventory_issues.csv` | Deterministic wallet review issues |
| `analysis/inventory/location_inventory_summary.json` | Location inventory counts |
| `analysis/reconciliation/` | Baseline oracle validation outputs |
| `outputs/logs/round_log.csv` | Round log seeded by the dev-only oracle `round scaffold` workflow |
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
| `source normalize` | Produce fact, balance, and evidence artifacts |
| `output render file` | Render an output-adapter artifact from facts |
| `checkpoint rebuild-location-inventory` | Aggregate location inventory artifacts |
| `checkpoint extract-pdf-balances` | Extract balances from supported PDF statements |
| `python -m tools.oracles.cli batch screen` | Validate and screen a candidate without copying it |
| `python -m tools.oracles.cli batch stage` | Screen and copy a passing candidate |
| `python -m tools.oracles.cli baseline validate` | Produce the full baseline oracle package |
| `python -m tools.oracles.cli verification compare` | Compare two verification export sets |
| `python -m tools.oracles.cli round scaffold` | Create a round folder and seed the round log |
| `python -m tools.oracles.cli source diff` | Compare candidate and reference ledger slices |

## Repo Tools

| Command | Purpose |
| ---- | ------- |
| `uv run python -m tools.scaffold_adapter ...` | Seed a package-style adapter with colocated tests and fixtures |
| `uv run python -m tools.refresh_adapter_goldens ...` | Refresh adapter-pack JSON goldens through the typed services |

## Agent Routes

| Path | Purpose |
| ---- | ------- |
| `.claude/commands/source-intake.md` | Intake, profile, normalize, checkpoint, and render a source |
| `.claude/commands/round-verification.md` | Dev-only oracle verification compare and round-close workflow |
| `.claude/commands/wallet-inventory.md` | Checkpoint location inventory rebuild workflow |
| `.claude/commands/normalization-exceptions.md` | Review normalization exceptions and reviews |
| `.claude/commands/source-diff.md` | Dev-only oracle candidate-versus-reference diff workflow |
| `.claude/commands/reconciliation-tax-build.md` | Architecture and implementation route for reconciliation, checkpointing, accounting, and tax |
| `.claude/commands/implementation-checkpoint.md` | Final implementation review, verification, and commit route |
| `.claude/commands/supporting-artifacts.md` | Checkpoint PDF balance extraction and supporting evidence workflow |
| `.claude/commands/adapter-authoring.md` | Adapter authoring and repair route |
