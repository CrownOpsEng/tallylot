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
- Do not add compatibility wrappers for removed legacy scripts.
- Do not let adapters reach across layers into CLI or config code.
- Keep application services on port contracts for adapter resolution and artifact
  persistence; do not import infrastructure modules from `application/`.
- Do not bypass `Decimal` with float-based financial calculations.
- Keep canonical events structurally strict: asset/amount pairs must be
  complete, and amounts must remain positive because direction is modeled by
  the `in`/`out` fields rather than signed numbers.
- Do not allow AI providers to mutate ledger records directly.
- Keep normalized evidence references portable by storing source-relative paths
  instead of machine-local absolute paths.
- Fail fast on ambiguous adapter matches and malformed adapter discovery
  contracts instead of silently picking a candidate.
- Keep adapter discovery narrow: discover only top-level adapter modules and
  package entry points so adapter-local tests and helpers can live beside the
  adapter without affecting runtime registration.

## Near-Term Enhancements

- Add richer baseline reconciliation artifacts.
- Add more conservative overlap heuristics and duplicate signatures.
- Expand source profiling to include richer file-family inspection.
- Add golden refresh tooling once more than one working source adapter exists.
