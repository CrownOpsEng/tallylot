---
title: "Current State"
summary: "Implemented runtime capabilities, current operational capabilities, and deferred areas."
doc_type: status
audience: human
owner: repo
status: active
naming_scope: current_state
nav_order: 10
---

This status page uses current implementation terms where accuracy requires
them. Forward-looking architecture and planning docs use the final target
product names `EvidenceSet`, `ClaimSet`, `EconomicFacts`,
`ReconciliationState`, `Checkpoint`, `Journal`, `TaxInputs`, and
`TaxOutputs`.

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

## Current Bridge To The Target Pipeline

- The implemented bridge currently centers on `EconomicActivityDraft`,
  `TransactionFact`, `balance_snapshots.csv`, and `balance_references.csv`.
- Treat that bridge as the current delivery boundary, not as the final architecture
  center.
- The target pipeline products and stage contracts live in
  `docs/concepts/pipeline-stage-contracts.md`; system-level trust gates and
  rollout alignment live in
  `docs/concepts/reconciliation-tax-architecture.md` and
  `docs/status/migration-sequence.md`.
- The live `src/tallylot/` package layout remains current-state truth.
  Forward-looking package ownership lives in
  `docs/concepts/domain-ontology.md` and `docs/standards/engineering.md`.
- MVP work should extend the current bridge incrementally where it protects the
  filing path, while adding richer pipeline products only when a concrete next
  stage needs them.

## Current Operational Surface

The repo currently ships typed replacements for the current workflow capabilities:

- workspace bootstrap
- source intake planning and apply with archive-aware reports, capture
  metadata, and the append-only capture registry
- source manifesting for settled raw captures
- capture-scoped source profiling with timezone provenance and a
  capture-scoped `profile_inventory.csv` discovery contract
- capture-scoped source normalization with explicit fact artifacts, derived
  balance snapshots, unified balance references, and archive member provenance
  under `working/normalized/captures/<capture_uid>/`
- planner-enabled capture normalization that writes
  `translation_input_candidates.json`, `translation_input_plan.json`, and
  `translation_input_issues.csv` before translation, blocks ambiguous file
  selection, and records translation planner metrics in
  `normalization_summary.json`
- planner-enabled Coinbase normalization also emits
  `working/products/evidence_sets/<evidence_set_id>/evidence_set.json` as the
  authoritative kernel for the bounded evidence-selection and typed
  statement-observation scope, with
  `working/products/evidence_sets/<evidence_set_id>/compatibility/translation_input_plan.json`
  as the derived compatibility plan
- planner-enabled Coinbase normalization also emits
  `working/products/claim_sets/<claim_set_id>/claim_set.json` plus deterministic
  claim-stage assessment sidecars and
  `compatibility/draft_projection_fields.json`, then derives the current
  `EconomicActivityDraft` bridge outputs from that persisted `ClaimSet`
- planner-enabled Coinbase normalization also emits
  `working/products/economic_facts/<economic_facts_id>/economic_facts.json`,
  one or more
  `working/products/reconciliation_states/<reconciliation_state_id>/reconciliation_state.json`,
  and zero or more
  `working/products/checkpoints/<checkpoint_id>/checkpoint.json`, each with
  product-local compatibility facts, snapshots, or references derived from the
  authoritative downstream kernels
- `ClaimSet`, `EconomicFacts`, `ReconciliationState`, and `Checkpoint` are
  therefore implemented authorities for the bounded planner-enabled Coinbase
  slice, while current readers still consume the mirrored compatibility
  `facts.csv`, `balance_snapshots.csv`, and `balance_references.csv` outputs
- `source normalize` now defaults to automatic target-product reruns:
  unchanged authoritative kernels are reused, changed authoritative inputs
  recalculate affected target products automatically, stale stage-owned
  outputs are pruned, and capture-local mirror files are rewritten from the
  current authoritative truth
- `source normalize --update-mode full-update` reuses unchanged authoritative
  kernels while refreshing all current stage-owned compatibility and detail
  outputs
- `source normalize --update-mode rebuild` bypasses fast-path reuse, rebuilds
  the implemented target-product chain from declared upstream truth, refreshes
  all current stage-owned detail, and still preserves deterministic ids and
  fingerprints on unchanged inputs
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
  the shared statement extraction path
- `application/balances` owns the shared balance capability: inspect, check,
  and summarize workflows with explicit drift, missing-side, duplicate-input,
  blocker outputs, additive cross-source corroboration sidecars, explicit
  `--as-of` target planning, offline-by-default checks, and optional provider
  hydration through separate balance-provider adapters
- dev-only oracle baseline validation with the documented artifact package
- dev-only oracle batch screening and staging with explicit issues, overlap
  summaries, and normalization window enforcement
- dev-only oracle verification comparison
- dev-only oracle round scaffolding and round-log seeding
- dev-only oracle source diff

## Current Developer Validation Tooling

- repo-native developer rebuild validation remains available via
  `make validate-workspace-replay`
  with optional expected-difference fixtures limited to issue and review count
  drift
- that tooling is developer-only proof tooling for rerun parity and migration
  validation; it is not a numbered operator workflow step and normal user
  workflows stay rerun-safe without a separate replay-validation step

## Current Hard Rules

- Raw evidence stays outside the repo in the external workspace.
- Untouched source originals stay under `evidence/raw/source/`.
- Normal user workflows are intended to stay rerun-safe and keep the fast path
  on ordinary commands rather than on manual rebuild validation.
- Automatic recalculation is the default normalization posture: changed
  authoritative inputs rerun affected stages or partitions without extra
  operator input, while unchanged authoritative partitions skip
  recalculation.
- `source normalize --update-mode full-update` refreshes stage-owned detail
  from authoritative truth without rebuilding unchanged kernels.
- `source normalize --update-mode rebuild` bypasses fast-path reuse for the
  implemented target-product chain while preserving deterministic unchanged
  outputs.
- `source profile` and `source normalize` accept only one materialized raw
  capture root under `evidence/raw/source/<source>/<capture_label>/` with
  matching `capture.json` metadata. They reject source roots, arbitrary
  directories, and mismatched capture metadata.
- Planner-enabled adapters describe translation input candidates and the
  normalization flow chooses the selected plan. If overlap, coverage, or
  freshness ambiguity would change the factual dataset, normalization stops
  before writing `facts.csv`, `balance_snapshots.csv`, or
  `balance_references.csv`.
- Those blocked planner runs still retain `evidence_set.json`, the product-local
  compatibility plan, the mirrored legacy `translation_input_plan.json`, and
  the legacy planner candidates and issues artifacts for operator review.
- Successful non-planner normalization leaves `evidence_set_id` and
  `evidence_set_ref` empty, and out-of-slice normalization also leaves the new
  downstream product ids and refs empty in response and summary surfaces.
- For planner-enabled Coinbase normalization,
  `translation_input_plan.json` is a compatibility view derived from the
  authoritative `EvidenceSet` kernel. The mirrored `facts.csv`,
  `balance_snapshots.csv`, and `balance_references.csv` artifacts are
  target-derived compatibility views owned by the downstream product kernels.
- Capture-scoped normalized outputs live under `working/normalized/captures/`.
- Reconciliation reads assembled source datasets under
  `working/normalized/sources/`.
- `profile_inventory.csv` is the downstream discovery contract for statement
  extraction and issue and review routing. It records capture-scoped fields
  such as `capture_uid`, `source`, `evidence_role`,
  `observed_period_start`, `observed_period_end`, `observed_period_label`,
  `statement_kind`, and `originality_class`.
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
  explicit unsupported cases until immutable identity is proven.
- `balance_snapshots.csv` and `balance_references.csv` are the only runtime
  balance artifacts. `balances.csv` and `balance_evidence.csv` are superseded
  generated outputs and are not runtime inputs.
- `tools.validate_workspace_replay` remains repo-native developer validation
  tooling for rebuild and migration proof. It compares capture-registry
  meaning parity, raw capture completeness, assembled source metrics, and
  reconciliation status counts. Optional expected-difference fixtures may
  declare only `issue_count_delta`, `review_count_delta`, and `reason`.
- Repo docs and repo-local agent entrypoints must describe only implemented
  commands and artifacts.

## Current Migration Notes

- Translation input planning is opt-in per adapter during the first increment.
- Coinbase is the first planner-enabled adapter and describes retail CSV
  candidates instead of choosing one file by path order.
- Legacy adapters still use the fallback `translate(...)` path until their
  candidate overlap and replacement rules are modeled well enough to migrate
  safely.

## Deferred Surface

- HTTP/API runtime
- SQLite-backed active storage
- provider-backed AI runtime
- concrete live balance-provider adapters and broad balance-provider support
  beyond the first public-ledger families
