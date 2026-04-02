# Roadmap

This file is the forward implementation anchor for future agents and engineers.
It tracks deferred work, explicit non-goals for the current phase, and design
decisions that should not be rediscovered from scratch.

## Current Phase

- Single-package Python architecture under `src/crypto_reconciliation/`
- External workspace model only
- CLI and library runtime only
- Filesystem-backed operational storage
- CoinTracking CSV as the only implemented output adapter
- Provider-agnostic AI interfaces with stub implementations

## Deferred Work

### HTTP And API Runtime

- Add a thin HTTP layer only over the existing application services.
- Do not let HTTP handlers own business rules, serialization policy, or adapter
  orchestration.
- Keep CLI and API requests on the same service contracts.

### Database Adoption

- Replace filesystem-backed canonical record storage with a real SQLite-backed
  implementation behind `StoragePort`.
- Keep raw evidence as files even after database adoption.
- Add migrations only when the SQLite implementation becomes active.

### Self-Contained AI Runtime

- Add provider-backed `ModelGateway` implementations for OpenAI and OAuth-based
  providers.
- Keep model providers read-only with respect to ledger mutation.
- Persist prompts, review findings, and evidence references in a structured
  audit trail.

### Source Adapter Expansion

- Add real blockchain adapters under `adapters/sources/blockchain/`.
- Add real platform API adapters under `adapters/sources/platform_api/`.
- Keep adapters self-contained with tests and metadata colocated.
- Preserve auto-discovery and fail fast on malformed adapter metadata.

## Rules For Future Work

- Do not reintroduce repo-local live workspace assumptions.
- Keep the retired legacy workspace roots out of git:
  `00_docs/`, `01_raw_exports/`, `02_working/`, `03_analysis/`,
  `04_import_ready/`, and `05_outputs/`.
- Keep repo-owned runbooks and agent-facing guides under `docs/`, and keep
  repo-owned workspace subtree guidance and templates under `docs/workspace/`.
- Treat workspace docs under the external root as live working copies or
  operator artifacts, not as the version-controlled source of truth.
- If workspace docs are ever refreshed or seeded beyond the minimal README,
  derive them from the repo-owned docs instead of maintaining a second manual
  documentation branch.
- Do not add compatibility wrappers for removed legacy scripts.
- Do not let adapters reach across layers into CLI or config code.
- Keep the agent guidance router-first: `AGENTS.md` should stay short and direct
  agents to narrow task-specific docs rather than front-loading broad repo
  context.
- Treat `docs/engineering-standards.md` as the code placement, typing,
  modularization, and naming contract.
- Treat `docs/commit-standards.md` as the commit message and stable-checkpoint
  contract. Use Conventional Commits and prefer small cohesive checkpoint
  commits without forcing micro-commit overhead.
- Keep application services on port contracts for adapter resolution and artifact
  persistence; do not import infrastructure modules from `application/`.
- Do not bypass `Decimal` with float-based financial calculations.
- Keep canonical events structurally strict: asset/amount pairs must be
  complete, and amounts must remain positive because direction is modeled by
  the `in`/`out` fields rather than signed numbers.
- Normalize raw sign conventions inside adapters when direction is otherwise
  explicit. If the sign is the only direction signal or it conflicts with other
  fields, surface an issue instead of guessing. When adapters do apply an
  interpretive normalization or fallback default, emit normalization review
  records so users can validate the behavior explicitly.
- Keep normalization review artifacts separate from hard issues: invalid or
  unsupported data stays in exceptions, while assumption-driven transforms and
  defaults go to normalization review reporting with concise grouped summaries.
- Do not allow AI providers to mutate ledger records directly.
- Keep normalized evidence references portable by storing source-relative paths
  instead of machine-local absolute paths.
- Fail fast on ambiguous adapter matches and malformed adapter discovery
  contracts instead of silently picking a candidate.
- Keep adapter discovery narrow: discover only top-level adapter modules and
  package entry points so adapter-local tests and helpers can live beside the
  adapter without affecting runtime registration.
- Refactor large modules before extending them materially. The current
  refactor-first hotspots are `adapters/sources/structured_csv.py`,
  `domain/models.py`, `interfaces/cli.py`, and
  `infrastructure/discovery/adapters.py`.
- The repo-local operational dataset was migrated to the external workspace on
  2026-03-26. Use this mapping for any future manual recovery or audit work:
  `00_docs -> docs`, `01_raw_exports/source -> evidence/raw/source`,
  `01_raw_exports/portfolio -> evidence/raw/portfolio`,
  `01_raw_exports/incoming -> evidence/raw/incoming`, `02_working -> working`,
  `03_analysis -> analysis`, `05_outputs -> outputs`.
- Treat `evidence/raw/incoming/` as a historical quarantine area for migrated
  catch-all evidence only. New intake should go directly to canonical capture
  paths under `evidence/raw/source/` or `evidence/raw/portfolio/`.
- The separate `04_import_ready/` root is retired in the current architecture.
  Keep approved import candidates under `working/import_batches/`.

## Near-Term Enhancements

- Add richer baseline reconciliation artifacts.
- Add more conservative overlap heuristics and duplicate signatures.
- Expand source profiling to include richer file-family inspection.
- Add golden refresh tooling once more than one working source adapter exists.
- Decompose the current hotspot modules into smaller, bounded packages or
  modules before they accumulate more responsibilities.
