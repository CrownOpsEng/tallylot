# Project State

## Current Runtime

- Typed single-package architecture under `src/crypto_reconciliation/`
- External workspace model only
- CLI and library interfaces only
- Filesystem-backed storage implementation
- CoinTracking CSV output adapter implemented
- Structured CSV source adapter implemented
- Blockchain, platform API, SQLite, and provider-backed AI remain stubs behind
  typed boundaries

## Current Operational Surface

The repo currently ships typed replacements for the core workflow capabilities:

- workspace bootstrap
- source manifesting
- source profiling with timezone provenance
- source normalization with CoinTracking candidate rendering
- wallet inventory rebuild with evidence, issues, and summary artifacts
- baseline validation with the documented artifact package
- batch screening and staging with explicit issues
- verification comparison
- round scaffolding and round-log seeding
- source reconciliation
- supported PDF balance extraction for Coinbase, Binance, and Shakepay style
  statements

## Current Hard Rules

- Raw evidence stays outside the repo in the external workspace.
- Profiling and normalization outputs must not be written inside raw evidence
  trees.
- Batch screening and staging are blocking gates. A blocked run still writes
  artifacts for review.
- Repo docs and repo-local agent entrypoints must describe only implemented
  commands and artifacts.

## Deferred Surface

- Additional real source adapters beyond the structured CSV adapter
- HTTP/API runtime
- SQLite-backed active storage
- provider-backed AI runtime
