# Implementation Migration Sequence

Use this document to implement the next phase without a big-bang refactor. The
goal is to move from the current canonical-event-centered flow to a
provider-neutral fact model with explicit parity gates.

## Migration Objectives

- preserve current working behavior while new foundations land
- avoid pushing more semantics into the legacy canonical event model
- keep adapters and services shippable at every checkpoint
- make CoinTracking compatibility a projection, not the center

## Phase 0. Schema Lock

Deliver before broad code changes:

- `TransactionFact` and supporting value objects
- layered classification enums
- runtime input and oracle boundaries
- migration acceptance criteria

Do not start tax-engine work before these contracts are written down.

## Phase 1. Boundary Models And Oracle Readers

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
- keep CoinTracking compatibility metadata out of the legacy canonical-event
  core while this phase lands

Exit criteria:

- oracle files parse deterministically
- no domain layer depends on CoinTracking row schemas

## Phase 2. Introduce Transaction Facts

Add the new domain packages and services for facts without removing the current
canonical path yet.

Implementation rule:

- normalization writes transaction facts first
- compatibility projections may still emit legacy canonical artifacts
- the old canonical shape becomes a downstream projection target
- until fact services land, keep CoinTracking candidate rendering as an
  explicit projection step rather than a normalization side effect

Exit criteria:

- at least one adapter writes fact artifacts and legacy artifacts in parallel
- parity tests prove the legacy outputs still match current expectations

## Phase 3. Migrate Reconciliation To Facts

Move these capabilities off canonical events:

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

Exit criteria:

- checkpoint assembly works from facts and source-backed evidence
- reconciliation artifacts no longer depend on canonical-event-specific fields

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

## Phase 6. Retire Canonical-First Workflows

Retire or demote the canonical-event-first path only after:

- adapter parity tests exist
- reconciliation no longer depends on canonical-event-specific assumptions
- accounting and tax consume facts directly
- CoinTracking output remains available as a compatibility projection

After this phase:

- canonical events remain a compatibility/output shape only
- new behavior must land in fact-based services first

## Parity Gates

Do not remove an older path until all relevant gates pass:

- parser or adapter contract tests
- projection parity tests
- reconciliation artifact parity where applicable
- end-to-end smoke workflow for the affected slice

## What Must Not Happen

- no big-bang rewrite
- no temporary wrappers that become permanent
- no new tax logic in adapters
- no new checkpoint logic in CoinTracking-specific code
- no direct use of CoinTracking tax reports as production state

## Required Follow-Through

When a task changes architecture, schema, or migration order:

- update `docs/architecture/reconciliation-tax-implementation-plan.md`
- update `ROADMAP.md`
- update this migration sequence if the checkpoint order changed
