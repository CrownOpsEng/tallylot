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
checkpoint, journal, and tax runtime.

Use it when making structural decisions that affect persistence,
reconciliation, checkpoint, journal, or tax computation. Treat it as a
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

- establish one evidence-backed, balance-confirmed checkpoint near `2026-03-23`
- use the `2023-08-05` CoinTracking export set as a historical oracle, not a
  hard checkpoint
- compute forward tax state for `2023` to `2025`
- emit a deterministic journal and require its entry checks to pass
- surface unsupported or ambiguous truth as explicit gaps, reviews, and later
  stage blockers
- preserve one interface-neutral application surface so future CLI, HTTP, API,
  and agent entrypoints can share the same typed workflows

## Contract Owners

This page does not re-own every lower-level contract.

Use these pages as the detailed contract owners:

- [Current Bridge Contracts](current-bridge-contracts.md)
- [Bridge To Target Mapping](bridge-to-target-mapping.md)
- [First Upstream Slice Contract](../reference/first-upstream-slice-contract.md)
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
- claims preserve evidence-local meaning and explicit ambiguity
- economic facts assert only economic truth the system can prove safely
- reconciliation is the trust gate before checkpoint adoption, downstream
  journal emission, and tax
- checkpoint truth is accepted checkpoint state with explicit acceptance basis
- `Journal` expands accepted truth and runs entry checks; it does not repair
  truth
- `TaxInputs` assemble policy-ready inputs from reconciled economics plus
  accepted checkpoint truth
- selected tax policies decide treatment in `TaxOutputs`; they do not decide
  source meaning, reconciliation truth, checkpoint truth, or journal outcomes

## Source, Output, Oracle, And Persistence Boundaries

### Source Boundaries

- source adapters produce selected-evidence observations today and evidence-local
  claims later
- adapters may emit only safe bridge hints and safe evidence-local meaning
- when source-provided hierarchical location labels survive into evidence-local
  kernels, use target-owned field names such as `location_group_label` and
  `location_label` rather than source-era nouns in canonical target contracts
- adapters do not own reconciliation
- adapters do not own checkpoint acceptance
- adapters do not own journal expansion or entry checks
- adapters do not own tax policy

### Output Boundaries

- renderers consume downstream-owned products or approved compatibility
  views
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

## Authoritative Kernels Versus Compatibility Views

The target runtime uses one authoritative persisted kernel per declared
partition scope.

Rules:

- target products persist as JSON kernels with separate sidecars
- once a target product becomes authoritative for an in-scope family, bridge
  CSV files for that same scope become compatibility views only
- compatibility views remain valid during migration, but they are never
  peer authorities beside the target kernel
- consumers read one authority at a time:
  - unmigrated consumers read the derived compatibility view
  - migrated consumers read the authoritative target product directly
- compatibility views must stay reproducible from authoritative kernels
  for the duration of the compatibility window

## Authoritative Persistence Model

Forward-looking persistence rules:

- target product kernels persist as JSON documents
- every persisted kernel carries its declared product id in its product header
- product ids are distinct from `product_scope_id`
- upstream `*_ref` fields in the product header store product ids, never `product_scope_id`
  and
  never raw kernel fingerprints
- when a product id hashes ordered upstream header refs, the component array
  stays in the same canonical order as those header fields unless the owner
  page documents a stronger reason to differ
- product sidecars persist separately from kernels and are keyed by
  `product_scope_id` or narrower truthful record ids
- canonical readiness rollups stay stage- and domain-oriented;
  source-grouped views stay as operator views or
  compatibility views rather than as gap, review, or readiness record
  families or readiness rollups
- target basenames use the owning product or sidecar family directly
  rather than generic names or bridge-era qualifiers
- stable ids and helper refs keep the owning family stem once they cross
  product or stage boundaries; prefer names such as
  `claim_bundle_decision_id`, `checkpoint_proposal_id`, `JournalAccountRef`,
  and `JournalUnitRef` over shorter or mixed-family alternates
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
| `EconomicFacts` | claim-set-lineage-scoped |
| `ReconciliationState` | continuity-segment-scoped |
| `Checkpoint` | checkpoint-scoped |
| `Journal` | checkpoint-economic-lineage-scoped |
| `TaxInputs` | checkpoint-economic-lineage-scoped |
| `TaxOutputs` | tax-input-policy-year-scoped |

Rules:

- one persisted partition owns one stable kernel fingerprint
- one persisted partition owns one product id aligned with that partition
- partition boundaries are chosen by the dimensions the owning stage actually
  reduces over
- `Journal` and `TaxInputs` stay checkpoint-economic-lineage-scoped because
  both product ids hash the accepted checkpoint ref plus the ordered upstream
  `economic_facts_refs`
- `TaxOutputs` stays tax-input-policy-year-scoped because its product id hashes
  the authoritative `tax_inputs_ref` plus the selected `tax_policy_id` and
  `tax_year`
- migration-era workspace paths may still group later products under a
  source-scoped directory tree, but that filesystem placement does not make
  source identity part of downstream product naming or stable-id recipes
- target products may expose derived reporting views across several
  partitions, but those views do not replace the authoritative partition
  kernels
- `EvidenceSet`, `ClaimSet`, and `EconomicFacts` kernels each persist one
  whole-product kernel per declared partition
- one persisted `ReconciliationState` kernel owns one continuity-segment root
- one persisted `Checkpoint` kernel owns one checkpoint record
- one persisted `Journal` kernel owns one journal emission root
- one persisted `TaxInputs` kernel owns one tax-input emission root
- one persisted `TaxOutputs` kernel owns one tax-input-policy-year output root
- readers use product ids or narrower record ids for authoritative product
  lookup; `product_scope_id` remains for shared reporting plus
  gap/review/readiness attachment only

### Default Filesystem Placement

Use these paths in forward-looking docs and later implementation work:

- `working/products/evidence_sets/<evidence_set_id>/evidence_set.json`
- `working/products/claim_sets/<claim_set_id>/claim_set.json`
- `working/products/economic_facts/<economic_facts_id>/economic_facts.json`
- `working/products/reconciliation_states/<reconciliation_state_id>/reconciliation_state.json`
- `working/products/checkpoints/<checkpoint_id>/checkpoint.json`
- `working/products/journals/<journal_id>/journal.json`
- `working/products/tax_inputs/<tax_inputs_id>/tax_inputs.json`
- `working/products/tax_outputs/<tax_outputs_id>/tax_outputs.json`
- stage-owned gap, review, and readiness sidecars live beside the
  authoritative kernel in that
  same product directory under `support/gap/`, `support/review/`, and
  `support/readiness/`, using `support/gap/gap_records.json`,
  `support/gap/gap_explanations.json`,
  `support/review/review_records.json`,
  `support/review/review_explanations.json`,
  `support/readiness/readiness_records.json`, and
  `support/readiness/readiness_rollup_records.json`
- compatibility views live under the authoritative product they depend on,
  for example:
  - `working/products/economic_facts/<economic_facts_id>/compatibility/facts.csv`
  - `working/products/reconciliation_states/<reconciliation_state_id>/compatibility/balance_snapshots.csv`
  - `working/products/checkpoints/<checkpoint_id>/compatibility/balance_references.csv`

Rules:

- the external workspace remains the runtime location for evidence and emitted
  files
- authoritative target kernels use product-owned directory stems rather than
  migration-era source or checkpoint containers
- source-scoped or checkpoint-scoped workspace groupings remain valid only for
  current-state surfaces, compatibility views, or genuinely source-owned
  or checkpoint-owned packages
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
- journal entry checks
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

- provenance detail
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
| Checkpoint and journal | `checkpoint_id`, `journal_id`, `checkpoint_assertion_id`, `entry_id` |
| Tax | `tax_inputs_id`, `tax_outputs_id`, `tax_year`, `basis_pool_ref`, `tax_input_id`, `basis_transition_id`, `tax_output_id`, `tax_carry_forward_id`, `tax_unsupported_input_id` |

Rules:

- evidence selection comparisons stay bounded to one `selection_id`
- claim adjudication stays bounded to one `claim_scope_id` at a time
- economic reducers stay bounded to one `economic_facts_id` partition at a time
- reconciliation reducers may read one continuity segment plus its explicit
  upstream references; they must not rescan unrelated full-history partitions
  per balance target
- checkpoint reducers may read the declared `checkpoint_id` inputs plus
  explicit upstream refs; they must not treat `product_scope_id` as the
  product-join
  key
- tax reducers may read one tax year plus explicitly referenced tax
  carry-forward records for the relevant basis pools; they must not recompute
  unrelated years by default
- unbounded pairwise candidate comparison outside one deterministic selection
  group is not allowed
- full-history rescans per target are not allowed when a bounded partition or
  reusable materialized state exists

### Sidecars, Caches, And Indexes

Sidecars and caches are allowed where replay cost would otherwise become too
high.

Typical sidecar or cache surfaces include:

- evidence selection explanations
- claim-scope decision explanations
- reconciliation continuity explanations
- checkpoint acceptance reports
- journal entry-check reports
- tax carry-forward record indexes

Rules:

- sidecars are never the sole copy of business meaning
- sidecars may be keyed by `product_scope_id` or narrower truthful record ids,
  but
  they do not replace product ids for authoritative product lookup
- caches are always regenerable from authoritative kernels and upstream refs
- materialized indexes are allowed only when they accelerate declared product
  kernels rather than replacing them

Required hot-path indexes:

- `subject_ref + effective_at`
- `continuity_segment_id`
- checkpoint assertion `subject_ref + as_of`
- `tax_year + basis_pool_ref`

## Acceptance Rules

Before approving structural work in reconciliation, checkpoint, journal,
or tax, ask:

- does the design keep one authoritative kernel per partition scope
- can unmigrated consumers survive on compatibility views alone
- can migrated consumers read target products without bridge lookups
- is every hot-path field present in the kernel rather than in a sidecar
- can the stage replay deterministically from its upstream authorities

If the answer to any of these is no, the design is not ready.
