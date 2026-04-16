---
title: "Oracle Boundaries"
summary: "Boundary rules for normal runtime inputs, adapter inputs and outputs, and oracle-only comparison packages."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 30
---

Use this document to keep the next architecture phase platform-agnostic. It
defines which inputs are normal runtime truth surfaces, which ones are
optional adapter-format inputs or outputs, and which ones remain
oracle-only comparison packages.

The goal is simple: the system must be able to reconstruct, reconcile, journal,
and compute tax state from primary evidence and intentional checkpoints without
depending on any one portfolio tracker.

## Design Rules

- The current bridge centers on `TransactionFact` plus shared balance
  files, but the target pipeline extends beyond facts alone.
- The shared runtime should remain asset-class-agnostic even when current
  adapters or policies are crypto-first.
- Primary evidence and evidence-backed checkpoints are first-class.
- Operator confirmations may support runtime reconciliation, but they are a
  lower-trust reference input than primary evidence.
- Output and import adapters are optional edges, not central dependencies.
- Oracle-only packages are comparison aids only.
- No tax, reconciliation, or journal logic may require CoinTracking-specific
  report rows to exist.

## Input Classes

| Class | Examples | Allowed To Establish Runtime Truth | Required In Normal Workflow | Notes |
| ---- | ---- | ---- | ---- | ---- |
| Primary evidence | platform exports, custody exports, statements, explorer exports | Yes | Yes | Primary reconstruction path |
| Checkpoint evidence | balance statements, location snapshots, accepted opening-state packages | Yes | Yes | First-class reconciliation input |
| Adapter-format inputs | CoinTracking trade imports, CoinTracking CSV shape, future tracker imports | Yes | No | Supported through adapters only |
| Oracle support packages | CoinTracking tax reports, roll-forward reports, average purchase price, double-entry journal exports | No | No | Development and validation only; never production runtime inputs |
| Derived outputs | CoinTracking export projection, double-entry journal export, `TaxOutputs` package, `Checkpoint` kernels plus support sidecars | No | No | Produced by the system |

## Normal Runtime Workflow

The normal filing-capable workflow is:

1. Ingest primary evidence.
2. Select evidence and emit evidence-local claims.
3. Compile accepted economics.
4. Reconcile continuity, transfers, and balance targets.
5. Accept checkpoints.
6. Emit a journal and run its entry checks.
7. Build `TaxInputs` from reconciled economics plus accepted checkpoint truth.
8. Apply selected tax policies to emit `TaxOutputs`.

This workflow must remain valid even when no CoinTracking tax outputs are
available.

The detailed target product flow behind that workflow is:

`EvidenceSet -> ClaimSet -> EconomicFacts -> ReconciliationState -> Checkpoint -> Journal -> TaxInputs -> TaxOutputs`

Current runtime note:

- today's bridge path still centers on `TransactionFact` plus shared balance
  files
- treat that bridge as an incremental delivery boundary, not as the long-term
  endpoint of the architecture

## CoinTracking-Specific Rules

CoinTracking support is intentionally narrow:

- CoinTracking import/export shapes may be supported as adapters.
- CoinTracking row types may be targeted by adapter-local renderer mappings
  when producing that export output.
- CoinTracking reports may be parsed for comparison by dev-only tooling.
- CoinTracking tax outputs may be used as black-box oracles during validation.

CoinTracking support must not expand into:

- required runtime inputs for tax computation
- required runtime inputs for checkpoint assembly
- shared domain enums or invariants that only exist because CoinTracking has
  them
- business logic keyed primarily on CoinTracking report columns

## Oracle-Only Package Policy

Oracle-only packages are valuable, but they are not part of the shared runtime
contract.

They are development and validation aids only, not production dependencies.

Permitted uses:

- regression testing
- black-box comparison against internal calculations
- historical sanity checks
- implementation review during migration

Forbidden uses:

- seeding production ACB pools directly from CoinTracking tax reports unless an
  explicit checkpoint import workflow adopts them as one-time opening state
- branching tax logic based on CoinTracking-specific output rows
- treating CoinTracking accounting exports as the internal ledger of record

## Checkpoint Rules

Checkpoints must be derived from primary evidence or from an explicit
checkpoint-import workflow.

Operator-confirmed balance references may unblock runtime balance checks, but
they do not satisfy filing-ready checkpoint requirements by themselves.

A valid checkpoint may be built from:

- custodial balance evidence
- location balance evidence
- statement evidence
- evidence-backed inventory proofs
- an intentionally adopted opening-state package with provenance

A valid checkpoint must not require:

- CoinTracking roll-forward output
- CoinTracking tax-year reports
- CoinTracking average purchase price reports

Those packages and reports may support comparison, but not checkpoint
existence.

## Architecture Guardrails

- Keep oracle parsing and comparison under `tools/oracles/`, not under
  `src/tallylot/`.
- Keep import-shape parsing behind adapter boundaries.
- Keep domain services unaware of CoinTracking report schemas.
- Keep crypto-, FX-, and security-specific terms out of shared runtime
  abstractions unless the concept is inherently specific to that adapter or
  output.
  When a source literally uses a term such as `wallet`, preserve it in
  evidence-stage records or adapter-local labels rather than in canonical
  target product names.
- Keep tax policy operating on `TaxInputs` built from reconciled economics and
  accepted checkpoint truth only.
- Keep journal rendering operating on reconciled economics, accepted checkpoint
  truth, and journal entry-check rules only.

## Failure Test

Ask this before approving new design work:

> If CoinTracking disappeared tomorrow, would the system still reconstruct,
> reconcile, checkpoint, journal, and compute taxes from primary evidence?

If the answer is no, the design has drifted out of bounds.
