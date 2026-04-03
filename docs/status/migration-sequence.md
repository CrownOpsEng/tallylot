---
title: "Migration Sequence"
summary: "Incremental migration order from the legacy normalized flow to the provider-neutral fact model."
doc_type: status
audience: human
owner: repo
status: active
nav_order: 20
---

Use this document to implement the next phase without a big-bang refactor. The
goal is to move from the current normalized-transaction flow to a
provider-neutral fact model with explicit parity gates.

## Migration Objectives

- preserve current working behavior while new foundations land
- avoid pushing more semantics into the current normalized transaction model
- keep adapters and services shippable at every checkpoint
- keep CoinTracking as one edge projection, not a migration anchor

## Phase 0. Schema Lock

Deliver before broad code changes:

- `TransactionFact` and supporting value objects
- layered classification enums
- runtime input and oracle boundaries
- migration acceptance criteria

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
  `*_at` plus `*_precision` temporal convention as part of the canonical fact
  contract
- replace the normalized transaction artifact set directly once the fact path is
  ready
- replace the current fact artifact schema directly for this branch rather than
  preserving a second active canonical model
- CoinTracking output remains an adapter projection, not a second core model
- until fact services land, keep CoinTracking candidate rendering as an
  explicit projection step rather than a normalization side effect

Bridge rule for the current branch:

- source adapters translate provider exports into `EconomicActivityDraft`
- adapter resolution remains registry-driven; shared support must not depend on
  concrete adapter ids or hand-maintained provider lists
- shared compiler code produces transaction facts
- shared projection code produces CoinTracking CSV rows
- application services, not adapters, derive runtime balances from translated
  activity unless the source provides real balance evidence
- unresolved or ambiguous identifier resolution blocks fact emission for the
  affected activity and must surface both review output and a blocking issue
- no parallel canonical runtime, wrapper lane, or runtime artifact translators
- a clean fact artifact schema break is allowed in this branch when the
  canonical replacement is ready
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

Rules:

- reconciliation consumes facts plus checkpoint evidence only
- CoinTracking tax outputs stay in oracle comparison services
- deterministic corrections such as redistributions must live in typed rules or
  fact metadata, not operator notes
- row-level candidate-versus-reference CSV comparison is a `source diff`
  utility, not the reconciliation service surface
- reconciliation advances in parallel with the accounting slice once the
  canonical fact shape is stable
- reconciliation remains the gate before tax and before treating rebuilt fact
  history as trusted

Exit criteria:

- checkpoint assembly works from facts and source-backed evidence
- reconciliation artifacts no longer depend on normalized-transaction-specific
  stopgaps

## Phase 4. Add Accounting Layer

Implement:

- internal journal model
- renderer port
- Ledger CLI renderer
- journal validation result artifacts

Rules:

- accounting consumes facts plus journal intents
- CoinTracking double-entry is comparison-only
- unsupported activity must surface as explicit journal coverage gaps
- accounting advances in parallel with reconciliation once the canonical fact
  shape is stable
- accounting is the journal structure and coverage validator, not the evidence
  truth gate

Exit criteria:

- supported activity renders and validates in Ledger CLI
- accounting balance checks line up with checkpoint outputs

## Phase 5. Add Tax Policy Layer

Implement:

- tax policy port
- Canada MVP policy
- pooled ACB state
- disposition and income outputs
- unsupported tax item outputs

Rules:

- tax computation consumes reconciled facts and intentional opening state only
- CoinTracking tax outputs are oracle-only
- no tax logic branches directly on CoinTracking report rows

Exit criteria:

- `2023` to `2025` tax artifacts emit from reconciled facts
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

## What Must Not Happen

- no big-bang rewrite
- no temporary wrappers that become permanent
- no provider-local adapter glue for compilation, projection, or synthetic
  balance assembly
- no new tax logic in adapters
- no new checkpoint logic in CoinTracking-specific code
- no direct use of CoinTracking tax reports as production state

## Required Follow-Through

When a task changes architecture, schema, or migration order:

- update `docs/concepts/reconciliation-tax-architecture.md`
- update `ROADMAP.md`
- update this migration sequence if the checkpoint order changed
