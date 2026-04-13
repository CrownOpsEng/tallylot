---
title: "Oracle Boundaries"
summary: "Boundary rules for normal runtime inputs, adapter surfaces, and oracle-only artifacts."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 30
---

Use this document to keep the next architecture phase platform-agnostic. It
defines which artifacts are normal runtime inputs, which ones are optional
adapter-format surfaces, and which ones are oracle-only support files.

The goal is simple: the system must be able to reconstruct, reconcile, journal,
and compute tax state from source evidence and intentional checkpoints without
depending on any one portfolio tracker.

## Design Rules

- The current bridge system of record is the provider-neutral transaction fact
  model, but the target canonical pipeline extends beyond facts alone.
- The internal core should remain asset-class-agnostic even when current
  adapters or policies are crypto-first.
- Source evidence and source-backed checkpoints are first-class.
- Operator confirmations may support runtime reconciliation, but they are a
  lower-trust reference surface than source-backed evidence.
- Output and import adapters are optional edges, not central dependencies.
- Oracle artifacts are comparison aids only.
- No tax, reconciliation, or journal logic may require CoinTracking-specific
  report rows to exist.

## Input Classes

| Class | Examples | Allowed To Create Core Facts | Required In Normal Workflow | Notes |
| ---- | ---- | ---- | ---- | ---- |
| Source evidence | exchange exports, wallet exports, statements, explorer exports | Yes | Yes | Primary reconstruction path |
| Checkpoint evidence | balance statements, wallet snapshots, source-backed checkpoint packages | Yes | Yes | First-class reconciliation input |
| Adapter-format inputs | CoinTracking trade imports, CoinTracking CSV shape, future tracker imports | Yes | No | Supported through adapters only |
| Oracle support artifacts | CoinTracking tax reports, roll-forward reports, average purchase price, double-entry exports | No | No | Development and validation only; never production runtime inputs |
| Derived outputs | CoinTracking export projection, Ledger journal, tax package, checkpoint package | No | No | Produced by the system |

## Normal Runtime Workflow

The normal filing-capable workflow is:

1. Ingest source evidence.
2. Normalize to transaction facts.
3. Reconcile transfers, balances, and reconciliation windows.
4. Build or validate checkpoints.
5. Render a double-entry journal.
6. Compute tax state from reconciled facts.
7. Emit filing artifacts.

This workflow must remain valid even when no CoinTracking tax outputs are
available.

The detailed target product flow behind that workflow is:

`EvidenceBundle -> ClaimBundle -> EconomicDataset -> ReconciliationDataset -> CheckpointPackage -> JournalDataset -> TaxDeterminantDataset -> TaxOutputDataset`

Current runtime note:

- today's bridge path still centers on `TransactionFact` plus shared balance
  artifacts
- treat that bridge as an incremental delivery seam, not as the long-term
  endpoint of the architecture

## CoinTracking-Specific Rules

CoinTracking support is intentionally narrow:

- CoinTracking import/export shapes may be supported as adapters.
- CoinTracking row types may be targeted by adapter-local renderer mappings
  when producing that export surface.
- CoinTracking reports may be parsed for comparison by dev-only tooling.
- CoinTracking tax outputs may be used as black-box oracles during validation.

CoinTracking support must not expand into:

- required runtime inputs for tax computation
- required runtime inputs for checkpoint assembly
- core domain enums or invariants that only exist because CoinTracking has
  them
- business logic keyed primarily on CoinTracking report columns

## Oracle-Only Artifact Policy

Oracle-only artifacts are valuable, but they are not part of the core runtime
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

Checkpoints must be derived from source-backed evidence or from an explicit
checkpoint-import workflow.

Operator-confirmed balance references may unblock runtime balance checks, but
they do not satisfy filing-ready checkpoint requirements by themselves.

A valid checkpoint may be built from:

- exchange balances
- wallet balances
- statement evidence
- source-backed inventory proofs
- an intentionally adopted opening-state package with provenance

A valid checkpoint must not require:

- CoinTracking roll-forward output
- CoinTracking tax-year reports
- CoinTracking average purchase price reports

Those artifacts may support comparison, but not checkpoint existence.

## Architecture Guardrails

- Keep oracle parsing and comparison under `tools/oracles/`, not under
  `src/tallylot/`.
- Keep import-shape parsing behind adapter boundaries.
- Keep domain services unaware of CoinTracking report schemas.
- Keep crypto-, FX-, and security-specific terms out of shared core abstractions
  unless the concept is inherently specific to that surface.
- Keep tax policy operating on reconciled economics and accepted checkpoint
  truth only.
- Keep journal rendering operating on reconciled economics, accepted checkpoint
  truth, and accounting coverage rules only.

## Failure Test

Ask this before approving new design work:

> If CoinTracking disappeared tomorrow, would the system still reconstruct,
> reconcile, checkpoint, journal, and compute taxes from source evidence?

If the answer is no, the design has drifted out of bounds.
