---
title: "Current State"
summary: "Implemented runtime capabilities, current operational surface, and deferred areas."
doc_type: status
audience: human
owner: repo
status: active
nav_order: 10
---

## Current Runtime

- Typed single-package architecture under `src/tallylot/`
- External workspace model only
- CLI and library interfaces only
- Filesystem-backed storage implementation
- Generic file output renderer with one implemented CSV edge adapter:
  `cointracking_csv`
- Restored real source adapters for Coinbase, Wealthsimple, Binance,
  Crypto.com, Shakepay, Ledger Live, Near, Ronin, GTrade, EVM explorer, EVM
  wallet-state, plus the generic structured CSV adapter
- Universal ZIP inspection enabled by default for source scanning workflows
- Separate balance-provider discovery is wired at runtime with discoverable
  `evm_json_rpc` and `near_rpc` family stubs, while concrete live network
  provider adapters remain deferred
- Platform API expansion, SQLite, and provider-backed AI remain stubbed behind
  typed boundaries

## Current Operational Surface

The repo currently ships typed replacements for the core workflow capabilities:

- workspace bootstrap
- source intake planning and apply with archive-aware reports, capture
  metadata, and the append-only capture registry
- source manifesting for settled raw captures
- capture-scoped source profiling with timezone provenance and a
  capture-scoped `profile_inventory.csv` discovery contract
- capture-scoped source normalization with explicit fact artifacts, derived
  balance snapshots, unified balance references, and archive member provenance
  under `working/normalized/captures/<capture_uid>/`
- source assembly via `source assemble`, producing reconciliation-ready source
  datasets under `working/normalized/sources/<source>/` and rewrites its owned
  generated artifact set on rerun
- shared statement extraction used by normalization and
  `checkpoint extract-pdf-balances`
- normalization-owned statement-backed `source_document` balance references for
  supported provider statements and constrained same-source-chain MetaMask
  portfolio evidence
- native and contract-backed EVM asset ids, native NEAR asset ids, and
  explicit unsupported issues for symbol-only public-ledger tokens when
  immutable asset ids cannot be proven
- checkpoint-owned manual balance submission scaffolding and validation that
  materializes balance snapshots, operator assertion references, and optional
  location inventory outputs
- checkpoint location inventory rebuild with evidence, issues, and summary
  artifacts
- checkpoint PDF balance extraction for supported statement families through
  the shared statement extraction seam
- `application/balances` owns the shared balance capability: inspect, check,
  and summarize workflows with explicit drift, missing-side, duplicate-input,
  blocker outputs, additive cross-source corroboration sidecars, explicit
  `--as-of` target planning, offline-by-default checks, and optional provider
  hydration through separate balance-provider adapters
- repo-native workspace replay validation via
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.validate_workspace_replay`
  with optional expected-difference fixtures limited to issue and review count
  drift
- dev-only oracle baseline validation with the documented artifact package
- dev-only oracle batch screening and staging with explicit issues, overlap
  summaries, and normalization window enforcement
- dev-only oracle verification comparison
- dev-only oracle round scaffolding and round-log seeding
- dev-only oracle source diff

## Current Hard Rules

- Raw evidence stays outside the repo in the external workspace.
- Untouched source originals stay under `evidence/raw/source/`.
- `source profile` and `source normalize` accept only one materialized raw
  capture root under `evidence/raw/source/<source>/<capture_label>/` with
  matching `capture.json` metadata. They reject source roots, arbitrary
  directories, and mismatched capture metadata.
- Capture-scoped normalized outputs live under `working/normalized/captures/`.
- Reconciliation reads assembled source datasets under
  `working/normalized/sources/`.
- `profile_inventory.csv` is the downstream discovery contract for statement
  extraction and issue or review context. It records capture-scoped fields such
  as `capture_uid`, `source`, `evidence_role`, `observed_period_start`,
  `observed_period_end`, `observed_period_label`, `statement_kind`, and
  `originality_class`.
- Provenance stays typed in runtime models and is flattened only at artifact
  boundaries. `balance_references.csv` uses the shared locator-support fields
  available for the emitting reference kind; `exceptions.csv` and
  `normalization_reviews.csv` use the same locator family with `raw_` prefixes
  plus `raw_row_ref`; aggregate location inventory evidence uses the same
  locator family with `evidence_` prefixes.
- ZIP inspection is on by default unless a command explicitly opts out.
- Dev-only oracle batch screening and staging are blocking gates. A blocked run
  still writes artifacts for review.
- Manual balance submission packages under
  `working/supporting_artifacts/balance_submissions/` are preliminary support
  artifacts. Balance outputs still live under the chosen assembled source root,
  normally `working/normalized/sources/<source>/`.
- Manual submission can unblock runtime reconciliation through
  `operator_assertion` references, but filing-ready checkpoint state still
  requires `source_document` evidence.
- Separate balance-provider adapters may hydrate missing references only for
  targets whose location and asset identity are already known.
- On-chain asset ids with immutable chain identity are the prerequisite for
  historical public-ledger provider hydration. Symbol-only token rows remain
  explicit unsupported surfaces until immutable identity is proven.
- `balance_snapshots.csv` and `balance_references.csv` are the only runtime
  balance artifacts. `balances.csv` and `balance_evidence.csv` are superseded
  generated outputs and are not runtime inputs.
- `tools.validate_workspace_replay` compares semantic capture-registry parity,
  raw capture completeness, assembled source metrics, and reconciliation status
  counts. Optional expected-difference fixtures may declare only
  `issue_count_delta`, `review_count_delta`, and `reason`.
- Repo docs and repo-local agent entrypoints must describe only implemented
  commands and artifacts.

## Deferred Surface

- HTTP/API runtime
- SQLite-backed active storage
- provider-backed AI runtime
- concrete live balance-provider adapters and broad balance-provider support
  beyond the first public-ledger families
