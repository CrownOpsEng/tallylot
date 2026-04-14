---
title: "Migration Sequence"
summary: "Incremental migration order from the current fact-path bridge to the final pipeline."
doc_type: status
audience: human
owner: repo
status: active
nav_order: 20
---

Use this document to implement the next phase without a big-bang refactor. The
goal is to move from the current normalized-transaction flow and current
fact-path bridge into the final pipeline with explicit parity gates and clean
retirement rules.

## Migration Objectives

- preserve current working behavior while new foundations land
- avoid pushing more semantics into the current normalized transaction model
- keep adapters and services shippable at every checkpoint
- keep CoinTracking as one edge projection, not a migration anchor
- preserve current bridge truth while establishing the final vocabulary for the
  future architecture

## Target Pipeline Landings

The target architecture should land as these final products:

1. `EvidenceSet`
2. `ClaimSet`
3. `EconomicFacts`
4. `ReconciliationState`
5. `Checkpoint`
6. `Journal`
7. `TaxInputs`
8. `TaxOutputs`

Migration rule:

- current `EconomicActivityDraft`, `TransactionFact`, and shared balance
  artifacts remain the active bridge into this pipeline
- do not freeze that bridge as the final architecture center
- land the richer pipeline products incrementally without restoring
  normalized-transaction-era wrapper lanes

## Current Bridge And Old-To-New Mapping

Current bridge truth:

- `EconomicActivityDraft`, `TransactionFact`, and shared balance artifacts are
  the live implementation seam
- that seam is the migration input and current parity baseline
- that seam is not the final architecture center

Final target-doc vocabulary:

| Current target-doc term | Final term |
| --- | --- |
| `EvidenceBundle` | `EvidenceSet` |
| `ClaimBundle` | `ClaimSet` |
| `EconomicDataset` | `EconomicFacts` |
| `ReconciliationDataset` | `ReconciliationState` |
| `CheckpointPackage` | `Checkpoint` |
| `JournalDataset` | `Journal` |
| `TaxDeterminantDataset` | `TaxInputs` |
| `TaxOutputDataset` | `TaxOutputs` |

Rules:

- current-state sections keep live implementation names where accuracy
  requires them
- target-state sections use the final names after this mapping is established
- do not keep dual active vocabularies once the mapping is clear

## Shared Foundations First

These foundations are prerequisites, not later cleanup:

- shared provenance family
- shared gap model and taxonomy
- shared readiness model and reducers
- shared checkpoint-assertion vocabulary
- explicit identity seams
- `SubjectRef`
- tax-policy selection contracts

Shared readiness uses this exact vocabulary:

- `semantic_ready`
- `reconciliation_ready`
- `checkpoint_ready`
- `accounting_ready`
- `tax_ready`

Readiness is sliceable by:

- source
- location
- instrument
- subject ref
- continuity segment
- checkpoint date
- tax year where relevant

Rules:

- this exact slice definition must stay identical everywhere it appears
- dataset readiness is derived from subject-level reducers
- no stage should invent an incompatible blocker or readiness surface

## Phase 0. Shared Foundations And Schema Lock

Deliver before broad code changes:

- `TransactionFact` and supporting value objects
- layered classification enums
- runtime input and oracle boundaries
- migration acceptance criteria
- shared provenance, gaps, readiness, checkpoint assertions, identity seams,
  `SubjectRef`, and tax-policy selection contracts

Do not start tax-engine work before these contracts are written down.

## Phase 1. Boundary Models And Dev-Only Oracle Readers

Introduce boundary-only models for:

- CoinTracking trade exports
- CoinTracking accounting exports
- CoinTracking tax or roll-forward exports
- checkpoint artifact contracts
- journal validation contracts

Rules:

- use `pydantic` here
- keep these models out of the core domain
- do not let oracle readers create production facts automatically
- keep CoinTracking-specific metadata out of the transaction fact core while
  this phase lands

Exit criteria:

- oracle files parse deterministically
- no domain layer depends on CoinTracking row schemas

## Phase 2. Introduce Transaction Facts

Add the new domain packages and services for facts without adding compatibility
wrappers around the current normalized transaction path.

Implementation rule:

- first land a fact-aligned adapter draft seam so working adapters stop
  constructing the temporary normalized artifact directly
- normalization writes transaction facts first
- introduce instrument identity, signed legs, stable leg ids, and the repo-wide
  `*_at` plus `*_precision` temporal convention as part of the shared fact
  contract
- replace the normalized transaction artifact set directly once the fact path is
  ready
- replace the current fact artifact schema directly for this branch rather than
  preserving a second active runtime model
- CoinTracking output remains an adapter projection, not a second core model
- until fact services land, keep CoinTracking candidate rendering as an
  explicit projection step rather than a normalization side effect

Bridge rule for the current branch:

- source adapters translate provider exports into `EconomicActivityDraft`
- introduce `ClaimSet` incrementally between evidence selection and final
  fact compilation when a source row cannot safely commit to one
  final economic meaning
- adapter resolution remains registry-driven; shared support must not depend on
  concrete adapter ids or hand-maintained provider lists
- shared compiler code produces transaction facts
- shared projection code produces CoinTracking CSV rows
- application services, not adapters, derive runtime balances from translated
  activity unless the source provides real balance evidence
- unresolved or ambiguous identifier resolution blocks fact emission for the
  affected activity and must surface both review output and a blocking issue
- ambiguous transfer, ownership, lifecycle, or mixed-purpose rows must be able
  to survive as source-local claims until one safe economic meaning
  is available
- no parallel runtime, wrapper lane, or runtime artifact translators
- a clean fact artifact schema break is allowed in this branch when the
  replacement is ready
- fact artifact readers must reject unknown `schema_version` values and the
  operational recovery path is full regeneration from raw evidence

Exit criteria:

- at least one adapter writes fact artifacts end to end
- fact artifacts fail fast when the schema version does not match the current
  reader
- projection tests prove the CoinTracking adapter still renders the expected
  external shape from the new facts

## Phase 3. Migrate Reconciliation To Facts

Move these capabilities off normalized transactions:

- transfer linking
- balance assertions
- checkpoint continuity
- correction chains
- reconciliation issue assembly
- reconciliation dataset and readiness reducers

Rules:

- reconciliation consumes facts plus checkpoint evidence only
- keep balance orchestration behind one shared balance capability for target
  planning, snapshot derivation, reference resolution, inspect and check
  workflows, hydration, corroboration, and assertion assembly
- treat exact balance assertions as one reconciliation input surface, not as the
  whole reconciliation product
- replace split balance evidence or confirmation artifacts directly with
  unified `balance_references.csv`
- fact-backed balance checks derive snapshots from facts; manual-only balance
  checks consume explicit snapshot rows
- check defaults to offline resolution; provider hydration is opt-in
- keep historical API lookup in separate balance-provider adapters rather than
  in source adapters
- require immutable on-chain asset ids before public-ledger provider hydration
  is treated as supported runtime behavior
- keep symbol-only public-ledger asset ids as explicit unsupported outputs
  until immutable on-chain identity is available
- CoinTracking tax outputs stay in oracle comparison services
- deterministic corrections such as redistributions must live in typed rules or
  fact metadata, not operator notes
- row-level candidate-versus-reference CSV comparison is a `source diff`
  utility, not the reconciliation service surface
- reconciliation advances in parallel with the accounting slice once the
  shared fact shape is stable
- reconciliation remains the gate before tax and before treating rebuilt fact
  history as trusted
- readiness must be reducible by source, location, instrument, and continuity
  segment rather than only by whole-source summaries
- readiness must use the shared slice definition exactly:
  - source
  - location
  - instrument
  - subject ref
  - continuity segment
  - checkpoint date
  - tax year where relevant

Exit criteria:

- checkpoint assembly works from facts and source-backed evidence
- reconciliation resolves explicit balance targets from facts and unified
  references rather than from a latest-only balance artifact assumption
- reconciliation artifacts no longer depend on normalized-transaction-specific
  stopgaps

## Phase 4. Add Accounting Layer

Implement:

- internal journal model
- renderer port
- Ledger CLI renderer
- journal validation result artifacts

Rules:

- accounting consumes reconciled economics plus accepted checkpoint state
- CoinTracking double-entry is comparison-only
- unsupported activity must surface as explicit journal coverage gaps
- accounting advances in parallel with reconciliation once the shared fact
  shape is stable
- accounting is the journal structure and coverage validator, not the evidence
  truth gate
- accounting must not become a local repair layer for upstream fact or
  reconciliation gaps

Exit criteria:

- supported activity renders and validates in Ledger CLI
- accounting balance checks line up with checkpoint outputs

## Phase 5. Add Tax Policy Layer

Implement:

- tax policy port
- `TaxInputs` contracts
- Canada MVP policy
- pooled ACB state
- disposition and income outputs
- unsupported tax item outputs

Rules:

- tax computation consumes reconciled economics plus accepted checkpoint truth,
  including intentional opening-state adoption when that checkpoint path is
  used
- CoinTracking tax outputs are oracle-only
- no tax logic branches directly on CoinTracking report rows
- journal validation may corroborate tax readiness, but tax must not depend on
  renderer success when the required determinants are already known
- tax-owned unresolved determinants must remain explicit instead of being pushed
  back into reconciliation or adapter logic

Exit criteria:

- `2023` to `2025` tax outputs emit from `TaxInputs` built from reconciled
  economics plus accepted checkpoint truth
- internal year-end and carry-forward logic is reproducible without CoinTracking
  tax reports

## Phase 6. Retire The Current Normalized Workflow

Retire or demote the current normalized-transaction-first path only after:

- adapter parity tests exist
- reconciliation no longer depends on normalized-transaction-specific
  assumptions
- accounting and tax consume facts directly
- CoinTracking output remains available as an ordinary output adapter

After this phase, new behavior must land in fact-based services first and the
temporary normalized transaction shape should not continue as a second active
runtime model.

## Parity Gates

Do not remove an older path until all relevant gates pass:

- parser or adapter contract tests
- projection parity tests
- reconciliation artifact parity where applicable
- end-to-end smoke workflow for the affected slice

## Test Preservation

- no test deletions without explicit human approval
- no silent assertion removal
- no fixture simplification that hides previous edge-case coverage
- test relocation or renaming is acceptable only when behavior coverage is
  preserved or improved
- "updating tests to the new structure" is not acceptable if coverage is
  weakened

Every refactor slice that changes tests must state:

- what old behavior the tests covered
- where that same behavior is covered now
- whether the assertion got stronger, weaker, or simply moved
- whether any expectation changed because of an intentional product decision

## Retirement Rules

- retire bridge-era seams only after the replacement path passes the relevant
  parity gates
- remove obsolete structures cleanly instead of leaving wrapper lanes,
  compatibility shims, or parallel runtime models behind
- keep schema-version failures fast and explicit; recover by regeneration from
  evidence rather than compatibility backfills
- retire the current normalized workflow only after facts, reconciliation,
  checkpointing, accounting, and tax inputs or outputs cover the filing path
- when a replacement is ready, update the owning architecture, roadmap, and
  migration docs in the same checkpoint so the repo keeps one active direction

## What Must Not Happen

- no big-bang rewrite
- no temporary wrappers that become permanent
- no provider-local adapter glue for compilation, projection, or synthetic
  balance assembly
- no new tax logic in adapters
- no new checkpoint logic in CoinTracking-specific code
- no direct use of CoinTracking tax reports as production state
- no weakening of the shared readiness slice definition
- no collapse of `Contract` and `Position`
- no use of `SubjectRef` as a substitute for real domain modeling
- no wording that says tax outputs come directly from reconciled facts
- no silent test weakening or deletion

## Required Follow-Through

When a task changes architecture, schema, or migration order:

- update `docs/concepts/reconciliation-tax-architecture.md`
- update `ROADMAP.md`
- update this migration sequence if the checkpoint order changed
