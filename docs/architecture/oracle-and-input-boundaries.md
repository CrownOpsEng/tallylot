# Oracle And Input Boundaries

Use this document to keep the next architecture phase platform-agnostic. It
defines which artifacts are normal runtime inputs, which ones are optional
adapter-format surfaces, and which ones are oracle-only support files.

The goal is simple: the system must be able to reconstruct, reconcile, journal,
and compute tax state from source evidence and intentional checkpoints without
depending on any one portfolio tracker.

## Design Rules

- The core system of record is the provider-neutral transaction fact model.
- Source evidence and source-backed checkpoints are first-class.
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
3. Reconcile transfers, balances, and coverage windows.
4. Build or validate checkpoints.
5. Render a double-entry journal.
6. Compute tax state from reconciled facts.
7. Emit filing artifacts.

This workflow must remain valid even when no CoinTracking tax outputs are
available.

## CoinTracking-Specific Rules

CoinTracking support is intentionally narrow:

- CoinTracking import/export shapes may be supported as adapters.
- CoinTracking transaction types may be represented in output projection metadata.
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
- Keep tax policy operating on reconciled facts and checkpoint state only.
- Keep journal rendering operating on facts and accounting intents only.

## Failure Test

Ask this before approving new design work:

> If CoinTracking disappeared tomorrow, would the system still reconstruct,
> reconcile, checkpoint, journal, and compute taxes from source evidence?

If the answer is no, the design has drifted out of bounds.
