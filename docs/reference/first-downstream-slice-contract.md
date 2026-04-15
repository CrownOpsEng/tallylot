---
title: "First Downstream Slice Contract"
summary: "Bounded contract for the first Coinbase-first EconomicFacts, ReconciliationState, and Checkpoint increment."
doc_type: reference
audience: human
owner: repo
status: active
nav_order: 16
related:
  - docs/reference/first-slice-contract.md
  - docs/concepts/pipeline-stage-contracts.md
  - docs/reference/target-contract-primitives.md
  - docs/concepts/reconciliation-tax-architecture.md
  - docs/status/migration-sequence.md
  - ROADMAP.md
---

Use this page when implementing or reviewing the first bounded downstream slice
after the default Coinbase-first `EvidenceSet` and `ClaimSet` increment. This
document freezes scope, ids, fingerprints, replay, parity, and allowed drift
for the first `EconomicFacts -> ReconciliationState -> Checkpoint` landing
path.

## Slice Scope

The first downstream slice is:

- the Coinbase-first family already bounded by
  [First Slice Contract](first-slice-contract.md)
- accepted `EconomicEventRecord` and `EconomicLegRecord` emission for supported
  Coinbase retail activity and recognized statement-backed balance observations
- bounded `ReconciliationState` emission for continuity segments, exact balance
  targets, and checkpoint candidates over those in-scope economic facts
- bounded `Checkpoint` emission for statement-backed position-quantity
  assertions
- continued interoperability with current `TransactionFact`,
  `balance_snapshots.csv`, `balance_references.csv`, balance
  inspect/check/summarize flows, and `cointracking_csv`

The slice is not:

- a broad downstream migration for every source family
- a replacement for `Journal`, `TaxInputs`, or `TaxOutputs`
- a claim that cross-source transfer pairing is already solved
- a claim that operator-only checkpoint inputs satisfy filing-ready truth

## In-Scope Record Families

The slice may emit only these downstream kernel families:

| Product | Record family | In-scope constraints |
| --- | --- | --- |
| `EconomicFacts` | `EconomicEventRecord` | only `asset_movement`, `cash_movement`, `fee_or_rebate`, and `correction` event families |
| `EconomicFacts` | `EconomicLegRecord` | only `holding_change`, `cash_change`, `fee`, and `rebate` leg roles |
| `EconomicFacts` | `ValuationRecord` | zero rows by default; `valuation_ref_or_null` stays empty unless a later parity-preserving slice widens valuation support |
| `ReconciliationState` | `ContinuitySegmentRecord` | one segment per Coinbase-held position subject and one checkpoint date |
| `ReconciliationState` | `BalanceTargetRecord` | only `target_kind = exact_balance`, with inline `expected_value` and `observed_value_or_null` using `AssertionValue` |
| `ReconciliationState` | `CheckpointCandidateRecord` | only candidates supported by in-scope exact-balance targets and statement evidence |
| `Checkpoint` | `CheckpointRecord` | accepted container for in-scope checkpoint assertions only |
| `Checkpoint` | `CheckpointAssertionRecord` | only `assertion_kind = position_quantity`, with `accepted_value` using `AssertionValue` |

`LinkRecord` remains out of scope for this bounded slice. The first downstream
slice may emit no `LinkRecord` rows and still be complete.

## Bridge Interop Outputs

The slice must continue to produce the current bridge interop outputs without
inventing new bridge-only schemas:

- compiled `TransactionFact` records
- `balance_snapshots.csv`
- `balance_references.csv`
- current balance inspect/check/summarize outputs through the active
  application surface
- `cointracking_csv` rows through current renderer boundaries

## Id And Fingerprint Rules

Stable-id format:

- use the stable-id recipes owned by
  [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md)
- do not create slice-specific alternate id formats
- slice-specific bounds narrow which families and enum values are allowed, not
  how ids and fingerprints are computed

Slice-specific rules:

- `EconomicEventRecord` ids must remain stable on unchanged first-slice claim
  inputs and unchanged compilation decisions
- `EconomicLegRecord` ids must remain stable on unchanged accepted event
  structure, leg roles, subject refs, quantities, and valuation refs
- `valuation_ref_or_null` stays empty for the default Coinbase-first downstream
  slice unless a later parity-preserving slice explicitly widens valuation
  support
- `ContinuitySegmentRecord` subjects in this slice are limited to one Coinbase
  position subject per segment; do not mix multiple positions into one segment
- `BalanceTargetRecord` ids in this slice are limited to one exact
  statement-backed target per subject and as-of time, with `expected_value`
  and `observed_value_or_null` using the shared `AssertionValue` contract from
  [Target Contract Primitives](target-contract-primitives.md)
- `CheckpointCandidateRecord` ids in this slice must derive only from in-scope
  balance-target refs and statement-backed evidence refs
- `CheckpointAssertionRecord` ids in this slice must include the accepted-value
  fingerprint exactly as owned by
  [Target Contract Primitives](target-contract-primitives.md)

In-scope checkpoint vocabularies for the slice:

- `trust_level`:
  - `analysis_ready`
  - `filing_ready`
- `acceptance_basis`:
  - `source_document`
  - `reconciled_continuity`
- `evidence_class`:
  - `statement_balance`
- `continuity_proof`:
  - `direct_observation`
  - `reconciled_rollforward`

Not allowed in this slice:

- `operator_assertion`
- `adopted_opening_state`
- `platform_balance`
- `wallet_snapshot`
- `inventory_proof`
- `partial_continuity`

## Parity Gates

Unchanged first-slice inputs must preserve all of the following:

- accepted economic event ids and ordering
- accepted economic leg ids, ordering, and quantities
- `ContinuitySegmentRecord` ids and ordering
- `BalanceTargetRecord` ids, ordering, and statuses
- `CheckpointCandidateRecord` ids, ordering, and statuses
- `CheckpointAssertionRecord` ids, ordering, and accepted values
- compiled `TransactionFact` ordering and semantics
- `balance_snapshots.csv` content for in-scope evidence
- `balance_references.csv` content for in-scope evidence
- current balance inspect/check/summarize output for in-scope evidence
- `cointracking_csv` row ordering and field values

## Replay Gates

The slice is replay-safe only when repeated runs on unchanged evidence preserve:

- identical accepted `EconomicEventRecord` and `EconomicLegRecord` fingerprints
- identical `ContinuitySegmentRecord`, `BalanceTargetRecord`, and
  `CheckpointCandidateRecord` fingerprints
- identical `CheckpointRecord` and `CheckpointAssertionRecord` fingerprints
- identical compiled bridge fact fingerprints
- identical `balance_snapshots.csv` and `balance_references.csv` content for
  in-scope evidence
- identical balance inspect/check/summarize output for supported slice
  subjects
- identical `cointracking_csv` output for supported bridge facts

Replay checks must also prove that incidental input ordering changes do not
change event ids, leg ids, continuity segment ids, balance target ids,
checkpoint candidate ids, checkpoint assertion ids, or rendered output.

## Allowed Drift

Not allowed:

- drift in accepted event or leg kernel fields
- drift in continuity-segment, balance-target, checkpoint-candidate, or
  checkpoint-assertion kernel ids
- quantity, accepted-value, or checkpoint-trust drift
- bridge-output drift on unchanged in-scope evidence
- balance inspect/check/summarize drift on unchanged in-scope evidence

Allowed only when kernel ids, statuses, and fingerprints stay unchanged:

- richer explanation text
- additional non-kernel gap or readiness sidecars
- additional non-kernel envelope fields
- additional comparison detail that does not change product meaning

## Explicitly Out Of Scope

This bounded downstream slice does not:

- emit `LinkRecord` rows as a required success condition
- widen beyond the Coinbase-first family already bounded by
  [First Slice Contract](first-slice-contract.md)
- make operator-only checkpoint acceptance part of the filing path
- use adopted opening state as an accepted checkpoint basis
- define runtime `Journal`, `TaxInputs`, or `TaxOutputs`
- require broad balance-provider hydration or cross-source transfer pairing
- authorize a repo-wide adapter-family migration before the bounded slice lands
