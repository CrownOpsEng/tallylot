# Project State

## Current Runtime

- Typed single-package architecture under `src/tallylot/`
- External workspace model only
- CLI and library interfaces only
- Filesystem-backed storage implementation
- Generic file output renderer with one implemented CSV edge adapter:
  `cointracking_csv`
- Restored real source adapters for Coinbase, Wealthsimple, Binance,
  Crypto.com, Shakepay, Ledger Live, Near, GTrade, EVM explorer, EVM
  wallet-state, plus the generic structured CSV adapter
- Universal ZIP inspection enabled by default for source scanning workflows
- Blockchain, platform API, SQLite, and provider-backed AI remain stubs behind
  typed boundaries

## Current Operational Surface

The repo currently ships typed replacements for the core workflow capabilities:

- workspace bootstrap
- source manifesting
- source intake planning and apply with archive-aware reports
- source profiling with timezone provenance
- source normalization with explicit fact artifacts, balance evidence, and
  archive member provenance
- checkpoint location inventory rebuild with evidence, issues, and summary
  artifacts
- checkpoint PDF balance extraction for supported statement families
- dev-only oracle baseline validation with the documented artifact package
- dev-only oracle batch screening and staging with explicit issues, overlap
  summaries, and normalization window enforcement
- dev-only oracle verification comparison
- dev-only oracle round scaffolding and round-log seeding
- dev-only oracle source diff

## Current Hard Rules

- Raw evidence stays outside the repo in the external workspace.
- Profiling and normalization outputs must not be written inside raw evidence
  trees.
- ZIP inspection is on by default unless a command explicitly opts out.
- Dev-only oracle batch screening and staging are blocking gates. A blocked run
  still writes artifacts for review.
- Repo docs and repo-local agent entrypoints must describe only implemented
  commands and artifacts.

## Deferred Surface

- HTTP/API runtime
- SQLite-backed active storage
- provider-backed AI runtime
