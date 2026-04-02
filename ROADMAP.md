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
- Do not bypass `Decimal` with float-based financial calculations.
- Do not allow AI providers to mutate ledger records directly.

## Near-Term Enhancements

- Add richer baseline reconciliation artifacts.
- Add more conservative overlap heuristics and duplicate signatures.
- Expand source profiling to include richer file-family inspection.
- Add golden refresh tooling once more than one working source adapter exists.
