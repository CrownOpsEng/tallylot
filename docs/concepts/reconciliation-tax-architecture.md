---
title: "Reconciliation And Tax Architecture"
summary: "Design anchor for trust gates, performance rules, tax-policy architecture, and filing-critical rollout from the current bridge toward the target pipeline."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 20
---

This document is the implementation anchor for evolving the repo away from
tracker-dependent historical workflows and into an independent reconciliation,
checkpoint, accounting, and tax runtime.

Use it when making structural decisions that affect normalization,
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
- surface unsupported or ambiguous truth as explicit issues, reviews, and
  later-stage blockers
- preserve one interface-neutral application surface so future CLI, HTTP, API,
  and agent entrypoints can share the same typed workflows

## Active Bridge Note

The current runtime bridge centers on:

- `EconomicActivityDraft`
- `TransactionFact`
- `balance_snapshots.csv`
- `balance_references.csv`

That bridge is:

- the live implementation seam
- the current delivery path
- the current parity baseline
- not the final architecture center

Current operational surfaces that remain part of runtime truth:

- capture-scoped source profiling
- capture-scoped normalization
- planner-enabled normalization
- translation input candidates, plan, and blocking issues
- source assembly into `working/normalized/sources/<source>/`
- shared statement extraction
- statement-backed balance references
- checkpoint-owned manual balance submission scaffolding and validation
- checkpoint location inventory rebuild
- offline-by-default balance inspection and checking
- optional provider hydration through separate balance-provider adapters
- replay validation
- oracle comparison and verification workflows

## Contract Owners

This page does not re-own every lower-level contract.

Use these pages as the detailed contract owners:

- [Current Bridge Contracts](current-bridge-contracts.md)
- [Pipeline Stage Contracts](pipeline-stage-contracts.md)
- [Domain Ontology](domain-ontology.md)
- [Gaps And Readiness](gaps-and-readiness.md)
- [Transaction Classification](transaction-classification.md)
- [Oracle Boundaries](oracle-boundaries.md)

## Trust Gates

The target runtime pipeline is:

`EvidenceSet -> ClaimSet -> EconomicFacts -> ReconciliationState -> Checkpoint -> Journal -> TaxInputs -> TaxOutputs`

Trust and ownership rules:

- evidence selection is deterministic before semantic commitment
- claims preserve source-local meaning and explicit ambiguity
- economic facts assert only economic truth the system can prove safely
- reconciliation is the trust gate before checkpoint adoption, accounting, and
  tax
- checkpoint truth is accepted state with explicit acceptance basis
- accounting expands and validates accepted truth; it does not repair truth
- tax inputs assemble determinants from reconciled economics plus accepted
  checkpoint truth
- selected tax policies decide treatment in `TaxOutputs`; they do not decide
  source meaning, reconciliation truth, checkpoint truth, or accounting truth

## Source, Output, Oracle, And Persistence Boundaries

### Source Boundaries

- source adapters produce source-local evidence and bridge outputs today, and
  later source-local claims
- adapters may emit only safe bridge hints and safe source-local meaning
- adapters do not own reconciliation
- adapters do not own checkpoint acceptance
- adapters do not own accounting
- adapters do not own tax policy

### Output Boundaries

- renderers consume downstream-owned products
- renderer-specific constraints stay at the edge
- CoinTracking row rules remain output-adapter concerns only

### Oracle Boundaries

- CoinTracking import and export shapes may be supported at the edge
- CoinTracking reports remain oracle-only
- oracle parsing remains outside `src/tallylot/`
- the system must still reconstruct, reconcile, checkpoint, journal, and
  compute taxes if CoinTracking tax reports disappear

### Crypto Boundaries

- crypto is the current filing scope
- crypto is not the ontology center
- crypto-specific language belongs at adapter, policy, or output edges unless
  fundamentally required
- the core remains broad enough for non-crypto support later

### Persistence Boundaries

- persistence implements the model
- persistence does not define the model
- no core runtime type relies on filesystem path, CSV row order, or export
  shape as identity
- raw evidence remains file-backed even after future database adoption
- repository ports remain the persistence seam
- active SQLite rollout is deferred until after the filing-critical path is
  stable

## Performance Rules

The core pipeline must stay auditable, deterministic, replayable, and fast
enough for large-scale calculation.

### Hot Path

Inner-loop calculations for:

- reconciliation
- checkpoint continuity
- journal validation
- tax computation

must operate on compact typed records only.

Hot-path data should include:

- stable ids
- timestamps and effective times
- subject refs where the stage actually owns them
- location refs
- instrument refs
- signed quantities
- explicit link ids
- explicit state transitions
- valuations where computation requires them
- minimal classification hints only where needed

The hot path should not repeatedly join in:

- full provenance detail
- review records
- large issue text
- evidence metadata blobs
- renderer metadata
- adapter-local annotations that do not change computation

Those belong in sidecars and explanation layers.

### Deterministic Ordering

Reducers must use stable ordering:

- effective time when present
- otherwise event timestamp
- then deterministic tie-break keys such as source sequence, event id, or leg
  id

Rules:

- reducers must be deterministic
- replay must be consistent across runs
- ordering must not depend on incidental file order

### Partitioning

Expensive recalculation must be partitionable by the dimensions the owning
stage actually uses, including:

- source
- location
- instrument
- subject reference where applicable
- continuity segment where applicable
- checkpoint date where applicable
- tax year where applicable

Use derived reporting projections instead of forcing every stage to key every
record by every dimension.

### Materialized State

Materialized derived state is allowed where replay cost would otherwise become
too high.

Typical surfaces include:

- checkpoint state snapshots
- reconciliation continuity summaries
- position state snapshots where replay cost is material
- tax pool and carry-forward state by tax year
- validated posting aggregates where useful

Derived state remains replaceable and does not replace source-of-truth history.

### Reducer Design Rules

Prefer:

- linear or near-linear reducers over sorted subject streams
- explicit link records instead of repeated inference
- one-time normalization of ambiguous bridge data into later-stage structures
- reuse of prior state outputs when valid

Avoid:

- repeated global joins across the full history
- repeated scanning of unrelated sources or years
- repeated evidence-level parsing during later-stage calculations
- dynamic policy dispatch inside tight per-record loops

### Tax Performance Rules

Tax calculation should not recompute full acquisition history from scratch for
every output row if bounded state is available.

The design should support:

- tax-year partitioning
- carried-forward pool and state materialization
- determinant grouping by subject and tax year
- reuse of prior year-close state as next year-open state

Policy selection should be resolved before execution, not as dynamic branching
inside the hot loop.

## Tax Policy Architecture

Typed tax-policy selection is a foundation seam, not an afterthought.

### Required Contracts

- `TaxPolicyId`
- `TaxPolicyDescriptor`
- `TaxPolicy`
- `TaxPolicyRegistry`
- `ApplyTaxPoliciesRequest`
- `ApplyTaxPoliciesResponse`

### `TaxPolicyDescriptor`

Must include:

- stable id
- display name
- jurisdiction or regime code
- supported years or periods
- supported output families
- version
- limitations
- status:
  - `supported`
  - `partial`
  - `experimental`
  - `deferred`

### `TaxPolicy`

Consumes:

- one `TaxInputs`
- one execution context

Produces:

- one `TaxOutputs`
- tax-owned gaps
- unsupported or deferred outputs

### Selection Semantics

- one run may select one or more policy ids
- all selected policies run independently against the same input set
- one policy's unsupported coverage does not invalidate another's results
- unknown policy ids fail request validation immediately
- missing explicit selection and missing configured default also fail
  validation
- configured defaults live only at application, config, and interface
  boundaries
- the core must not assume one default jurisdiction

### Tax-Stage Ownership

Tax policy may decide:

- jurisdiction-specific treatment
- basis rules
- carry-forward rules
- output structure

Tax policy may not decide:

- source meaning
- economic truth
- reconciliation truth
- checkpoint truth
- accounting truth

### MVP Tax Scope

- keep the seam general
- implement Canada MVP first
- prioritize the filing path for `2023`, `2024`, and `2025`
- do not build a plugin platform

## Filing-Critical Acceptance Criteria

The system is filing-ready only when all of these are true:

- a source-backed checkpoint exists near `2026-03-23`
- no unresolved material reconciliation issues remain
- no unresolved material unsupported tax items remain
- journal validation passes for supported activity
- the forward-computed state from the `2023-08-05` historical oracle lands on
  the source-backed checkpoint
- `2023`, `2024`, and `2025` outputs can be reproduced from workspace evidence

## Materiality And Unsupported Cases

Default materiality rules:

- do not silently suppress any non-zero drift
- log every difference
- allow explicit immaterial waivers only in artifacts, never in code comments
- default immaterial threshold: `<= CAD 25` per asset and `<= CAD 250`
  aggregate
- do not auto-waive `CAD`, `BTC`, `ETH`, or stablecoins

Unsupported or ambiguous truth must produce explicit outputs and roadmap items.
Do not guess on:

- superficial loss treatment
- capital versus business account classification
- unsupported DeFi lifecycle cases
- NFTs
- bankruptcy or scam-loss workflows

## External Library Policy

Use directly when they are permissive and fit cleanly:

- Ledger CLI as the first journal validator
- RP2 as an architectural reference or narrow comparison source
- `tsiemens/acb` as a scenario and formula reference
- small MIT or Apache libraries only when the reuse is narrow and documented

Use for reference only:

- Beancount
- hledger
- GPL codebases, tests, or examples

Do not:

- copy GPL code into the repo
- lightly rewrite GPL implementations and treat them as original
- introduce heavy support libraries that fight the current typed architecture

## Rollout Alignment

The repo is moving from the current bridge toward the target stage contracts
incrementally, not through a big-bang rewrite.

Rollout rules:

- the current bridge remains the live runtime seam until a bounded slice lands
  a cleaner replacement
- no dual active runtime or compatibility-wrapper lane should survive once a
  clean replacement is ready
- current-state docs stay accurate about live bridge terms
- target docs stay explicit about the intended end state without claiming it is
  already implemented
- when work affects architecture, sequencing, or trust-gate ownership, update
  this page together with [ROADMAP.md](../../ROADMAP.md) and
  [Migration Sequence](../status/migration-sequence.md)

The detailed implementation order lives in:

- [ROADMAP.md](../../ROADMAP.md)
- [Migration Sequence](../status/migration-sequence.md)
