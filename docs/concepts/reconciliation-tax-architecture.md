---
title: "Reconciliation And Tax Architecture"
summary: "Design anchor for trust gates, persistence rules, performance rules, and filing-critical rollout from the current bridge toward the target pipeline."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 20
---

This document is the implementation anchor for evolving the repo away from
tracker-dependent historical workflows and into an independent reconciliation,
checkpoint, accounting, and tax runtime.

Use it when making structural decisions that affect persistence,
reconciliation, checkpointing, journaling, or tax computation. Treat it as a
design contract, not as a loose idea list.

## Current Runtime Note

Current runtime truth remains:

- typed application architecture under `src/tallylot/`
- CLI and library only
- filesystem-backed active storage
- SQLite deferred behind interfaces and ports
- provider-backed AI deferred behind interfaces and ports
- raw evidence outside the repo in the external workspace

The filing-critical output horizon remains `2023` through `2025`.

The system must:

- establish one source-backed, balance-confirmed checkpoint near `2026-03-23`
- use the `2023-08-05` CoinTracking export set as a historical oracle, not a
  hard checkpoint
- compute forward tax state for `2023` to `2025`
- render a deterministic double-entry journal and require it to validate
- surface unsupported or ambiguous truth as explicit gaps, reviews, and later
  stage blockers
- preserve one interface-neutral application surface so future CLI, HTTP, API,
  and agent entrypoints can share the same typed workflows

## Contract Owners

This page does not re-own every lower-level contract.

Use these pages as the detailed contract owners:

- [Current Bridge Contracts](current-bridge-contracts.md)
- [Bridge To Target Mapping](bridge-to-target-mapping.md)
- [First Slice Contract](../reference/first-slice-contract.md)
- [First Downstream Slice Contract](../reference/first-downstream-slice-contract.md)
- [Pipeline Stage Contracts](pipeline-stage-contracts.md)
- [Domain Ontology](domain-ontology.md)
- [Gaps And Readiness](gaps-and-readiness.md)
- [Engineering Standards](../standards/engineering.md)
- [Transaction Classification](transaction-classification.md)
- [Oracle Boundaries](oracle-boundaries.md)

## Trust Gates

The target runtime pipeline is:

`EvidenceSet -> ClaimSet -> EconomicFacts -> ReconciliationState -> Checkpoint -> Journal -> TaxInputs -> TaxOutputs`

Trust and ownership rules:

- evidence selection is deterministic before claim commitment
- claims preserve source-local meaning and explicit ambiguity
- economic facts assert only economic truth the system can prove safely
- reconciliation is the trust gate before checkpoint adoption, accounting, and
  tax
- checkpoint truth is accepted state with explicit acceptance basis
- accounting expands and validates accepted truth; it does not repair truth
- tax inputs assemble policy-ready tax inputs from reconciled economics plus accepted
  checkpoint truth
- selected tax policies decide treatment in `TaxOutputs`; they do not decide
  source meaning, reconciliation truth, checkpoint truth, or accounting truth

## Source, Output, Oracle, And Persistence Boundaries

### Source Boundaries

- source adapters produce source-local evidence today and source-local claims
  later
- adapters may emit only safe bridge hints and safe source-local meaning
- adapters do not own reconciliation
- adapters do not own checkpoint acceptance
- adapters do not own accounting
- adapters do not own tax policy

### Output Boundaries

- renderers consume downstream-owned products or approved compatibility
  projections
- renderer-specific constraints stay at the edge
- CoinTracking row rules remain output-adapter concerns only

### Oracle Boundaries

- CoinTracking import and export shapes may be supported at the edge
- CoinTracking reports remain oracle-only
- oracle parsing remains outside `src/tallylot/`
- the system must still reconstruct, reconcile, checkpoint, journal, and
  compute taxes if CoinTracking tax reports disappear

### Persistence Boundaries

- persistence implements the model
- persistence does not define the model
- no shared runtime type relies on filesystem path, CSV row order, or export
  shape as identity
- raw evidence remains file-backed even after future database adoption
- repository ports remain the persistence seam
- active SQLite rollout is deferred until after the filing-critical path is
  stable

## Authoritative Kernels Versus Compatibility Projections

The target runtime uses one authoritative persisted kernel per product scope.

Rules:

- target products persist as JSON kernels with separate sidecars
- once a target product becomes authoritative for an in-scope family, bridge
  CSV files for that same scope become compatibility projections only
- compatibility projections remain valid during migration, but they are never
  peer authorities beside the target kernel
- consumers read one authority at a time:
  - unmigrated consumers read the derived compatibility projection
  - migrated consumers read the target product kernel directly
- compatibility projections must stay reproducible from authoritative kernels
  for the duration of the compatibility window

## Authoritative Persistence Model

Forward-looking persistence rules:

- target product kernels persist as JSON documents
- every persisted kernel carries its declared product id in metadata
- product ids are distinct from `dataset_id`
- upstream `*_ref` metadata fields store product ids, never `dataset_id` and
  never raw kernel fingerprints
- product sidecars persist separately from kernels and are keyed by
  `dataset_id` or narrower truthful record ids
- target basenames use the owning product or support role directly
  rather than generic names or bridge-era qualifiers
- writes are replace-whole-partition operations, not append-in-place mutation
  of accepted truth
- persisted kernels are immutable snapshots for one declared partition scope
- sidecars are regenerable from authoritative kernels plus upstream refs
- caches and indexes are accelerators only; they are never the authority

### Default Partition Scopes

| Product | Default partition scope |
| --- | --- |
| `EvidenceSet` | capture-scoped |
| `ClaimSet` | capture-scoped |
| `EconomicFacts` | claim-lineage-scoped |
| `ReconciliationState` | continuity-segment-scoped |
| `Checkpoint` | checkpoint-set-scoped |
| `Journal` | journal-scoped under one checkpoint scope |
| `TaxInputs` | tax-input-set-scoped |
| `TaxOutputs` | policy-and-tax-year-scoped inside one tax-input scope |

Rules:

- one persisted partition owns one stable kernel fingerprint
- one persisted partition owns one product id aligned with that partition
- partition boundaries are chosen by the dimensions the owning stage actually
  reduces over
- migration-era workspace paths may still group later products under a
  source-scoped directory tree, but that filesystem placement does not make
  source identity part of downstream product naming or stable-id recipes
- target products may expose derived reporting projections across several
  partitions, but those projections do not replace the authoritative partition
  kernels
- `EvidenceSet`, `ClaimSet`, and `EconomicFacts` kernels each persist one
  whole-product kernel per declared partition
- one persisted `ReconciliationState` kernel owns one continuity-segment root
- one persisted `Checkpoint` kernel owns one checkpoint record
- one persisted `Journal` kernel owns one journal emission root
- one persisted `TaxInputs` kernel owns one tax-input emission root
- one persisted `TaxOutputs` kernel owns one policy-and-tax-year output root
- readers use product ids or narrower record ids for target-kernel lookup;
  `dataset_id` remains for shared support attachment and reporting only

### Default Filesystem Placement

Use these paths in forward-looking docs and later implementation work:

- `working/normalized/captures/<capture_uid>/evidence_set.json`
- `working/normalized/captures/<capture_uid>/claim_set.json`
- `working/normalized/captures/<capture_uid>/support/gaps.json`
- `working/normalized/captures/<capture_uid>/support/gap_explanations.json`
- `working/normalized/captures/<capture_uid>/support/reviews.json`
- `working/normalized/captures/<capture_uid>/support/review_explanations.json`
- `working/normalized/captures/<capture_uid>/support/readiness.json`
- `working/normalized/captures/<capture_uid>/support/readiness_summaries.json`
- `working/normalized/sources/<source>/economic_facts.json`
- `working/normalized/sources/<source>/bridge/facts.csv`
- `working/normalized/sources/<source>/bridge/balance_snapshots.csv`
- `working/normalized/sources/<source>/bridge/balance_references.csv`
- `working/normalized/sources/<source>/reconciliation/<continuity_segment_id>/reconciliation_state.json`
- `working/normalized/sources/<source>/reconciliation/<continuity_segment_id>/support/gaps.json`
- `working/normalized/sources/<source>/reconciliation/<continuity_segment_id>/support/gap_explanations.json`
- `working/normalized/sources/<source>/reconciliation/<continuity_segment_id>/support/reviews.json`
- `working/normalized/sources/<source>/reconciliation/<continuity_segment_id>/support/review_explanations.json`
- `working/normalized/sources/<source>/reconciliation/<continuity_segment_id>/support/readiness.json`
- `working/normalized/sources/<source>/reconciliation/<continuity_segment_id>/support/readiness_summaries.json`
- `outputs/checkpoints/<checkpoint_set_id>/checkpoint.json`
- `outputs/checkpoints/<checkpoint_set_id>/journal.json`
- `outputs/checkpoints/<checkpoint_set_id>/tax_inputs.json`
- `outputs/checkpoints/<checkpoint_set_id>/tax_outputs/<tax_policy_id>/<tax_year>.json`

Rules:

- the external workspace remains the runtime location for evidence and emitted
  files
- later implementation may add indexes or caches beside these kernels, but
  must not rename the authoritative kernel paths without updating the owner
  docs
- current-state docs remain accurate to the live bridge until implementation
  lands; this section owns only the target direction

### Replace Semantics

- writers replace the entire owned kernel for one partition on a successful run
- a rerun may refresh or prune stage-owned sidecars under the same partition
- reruns must not append stale kernel rows across runs
- later accepted truth supersedes earlier accepted truth through new records and
  explicit lineage, not through in-place mutation of an accepted kernel record

## Performance Rules

The target pipeline must stay auditable, deterministic, replayable, and fast
enough for large-scale calculation.

### Hot Path

Inner-loop calculations for:

- reconciliation
- checkpoint continuity
- journal validation
- tax computation

must operate on compact typed kernel records only.

Required hot-path content includes:

- stable ids
- timestamps and effective times
- subject refs where the stage actually owns them
- location refs
- instrument refs
- signed quantities
- direct assertion values where the stage owns them
- explicit link ids
- explicit state transitions
- valuations where computation requires them
- minimal classification hints only where needed

The hot path should not repeatedly join in:

- full provenance detail
- reviews
- large explanation text
- evidence sidecar detail
- renderer detail
- adapter-local annotations that do not change computation

Those belong in sidecars and explanation layers.

### Deterministic Ordering

Reducers must use stable ordering:

- effective time when present
- otherwise the product's canonical temporal key
- then deterministic tie-break keys such as stable ids

Rules:

- reducers must be deterministic
- replay must be consistent across runs
- ordering must not depend on incidental file order

### Partitioning

Expensive recalculation must be partitionable by the dimensions the owning
stage actually uses.

Required partition keys:

| Stage family | Required partition keys |
| --- | --- |
| Evidence and claims | `capture_uid`, `evidence_set_id`, `selection_id`, `claim_set_id`, `claim_scope_id` |
| Economic and reconciliation | `economic_facts_id`, `reconciliation_state_id`, `continuity_segment_id`, `balance_target_id`, `checkpoint_proposal_id` |
| Checkpoint and accounting | `checkpoint_set_id`, `journal_id`, `checkpoint_assertion_id`, `entry_id` |
| Tax | `tax_inputs_id`, `tax_outputs_id`, `tax_year`, `basis_pool_ref`, `tax_input_id`, `basis_transition_id` |

Rules:

- evidence selection comparisons stay bounded to one `selection_id`
- claim adjudication stays bounded to one `claim_scope_id` at a time
- economic reducers stay bounded to one `economic_facts_id` partition at a time
- reconciliation reducers may read one continuity segment plus its explicit
  upstream references; they must not rescan unrelated full-history partitions
  per balance target
- checkpoint reducers may read the declared `checkpoint_set_id` inputs plus
  explicit upstream refs; they must not treat `dataset_id` as the product-join
  key
- tax reducers may read one tax year plus explicitly referenced carry-forward
  basis-pool state; they must not recompute unrelated years by default
- unbounded pairwise candidate comparison outside one deterministic selection
  group is not allowed
- full-history rescans per target are not allowed when a bounded partition or
  reusable materialized state exists

### Sidecars, Caches, And Indexes

Sidecars and caches are allowed where replay cost would otherwise become too
high.

Typical sidecar or cache surfaces include:

- evidence selection summaries
- claim-scope decision summaries
- reconciliation continuity summaries
- checkpoint summaries
- journal validation summaries
- tax carry-forward state indexes

Rules:

- sidecars are never the sole copy of business meaning
- sidecars may be keyed by `dataset_id` or narrower truthful record ids, but
  they do not replace product ids for kernel lookup
- caches are always regenerable from authoritative kernels and upstream refs
- materialized indexes are allowed only when they accelerate declared product
  kernels rather than replacing them

Required hot-path indexes:

- `subject_ref + effective_at`
- `continuity_segment_id`
- `checkpoint_assertion` subject and date
- `tax_year + basis_pool_ref`

## Acceptance Rules

Before approving structural work in reconciliation, checkpointing, accounting,
or tax, ask:

- does the design keep one authoritative kernel per scope partition
- can unmigrated consumers survive on compatibility projections alone
- can migrated consumers read target products without bridge lookups
- is every hot-path field present in the kernel rather than in a sidecar
- can the stage replay deterministically from its upstream authorities

If the answer to any of these is no, the design is not ready.
