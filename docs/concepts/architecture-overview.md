---
title: "Architecture Overview"
summary: "High-level map of the current bridge, the target runtime pipeline, and the primary contract pages."
doc_type: concept
audience: human
owner: repo
status: active
naming_scope: forward_target
nav_order: 10
---

TallyLot is a typed Python package and CLI for evidence intake,
reconciliation, checkpoint acceptance, journal entry checks, rendering, and
tax computation.

## Runtime Posture

The live runtime still centers on the current bridge:

- `EconomicActivityDraft`
- `TransactionFact`
- `balance_snapshots.csv`
- `balance_references.csv`

That bridge is the current implementation boundary and parity baseline. It is
not the final architecture center.

The target runtime pipeline is:

`EvidenceSet -> ClaimSet -> EconomicFacts -> ReconciliationState -> Checkpoint -> Journal -> TaxInputs -> TaxOutputs`

Within that pipeline, `EvidenceSet` is already the implemented authority for
the bounded Coinbase evidence-selection slice, while `ClaimSet` is the next
upstream authority slice still to land.

The primary contract pages freeze product ids, product headers, critical-path
kernel field tables, and the compatibility sidecar boundary for retained legacy
hint fields.

Broader consumer-facing grouped or query surfaces remain intentionally
deferred. Through the tax-first path, grouped outputs may remain only as
tax-output-local derived content, narrow rendering-derived content, or
compatibility-local derived output rather than as a shared application center.
broader derived read models and projections stay deferred until a later capability-specific increment makes them necessary.

Gap and review remain shared contracts plus persisted shared-assessment
families. Readiness stays capability-owned derived behavior rather than shared
assessment truth. The owning application slice emits and reduces its own
assessment behavior until a specific capability-owned derived read-model
package is activated.

## Layer Shape

- `domain/` owns business models, refs, enums, and value objects
- `application/` owns use-case orchestration over domain models and ports
- `ports/` defines narrow typed boundaries
- `infrastructure/` implements ports
- `adapters/` translates source and output formats
- `interfaces/` exposes CLI entry points over application capabilities

Raw evidence and live workspace files remain in the external workspace, not
in the repo.

## Primary Contract Pages

These pages define the primary current-state and forward-looking contracts:

| Page | Owns |
| --- | --- |
| [Current Bridge Contracts](current-bridge-contracts.md) | live bridge truth and bridge surface rules |
| [Bridge To Target Mapping](bridge-to-target-mapping.md) | authoritative writer rules, compatibility views, and reader cutovers |
| [Pipeline Stage Contracts](pipeline-stage-contracts.md) | target product kernels, ids, ordering, and handoff rules |
| [Domain Ontology](domain-ontology.md) | identity seams, ref recipes, and package ownership |
| [Gap, Review, And Shared Attachment](gaps-and-reviews.md) | gap, review, `SubjectRef`, and shared attachment contracts plus readiness locality rules |
| [Reconciliation, Checkpoint, Journal, And Tax Architecture](reconciliation-tax-architecture.md) | reconciliation, checkpoint, journal, and tax trust gates plus persistence, partitioning, and fast-path rules |
| [Evidence And Claim Contract](../reference/evidence-claim-contract.md) | current bounded `EvidenceSet -> ClaimSet` contract scope |
| [Economics Reconciliation Checkpoint Contract](../reference/economics-reconciliation-checkpoint-contract.md) | current bounded `EconomicFacts -> ReconciliationState -> Checkpoint` contract scope |
| [ROADMAP.md](../../ROADMAP.md) | planning-only sequencing and later rollout detail |
| [Current State](../status/current-state.md) | implemented runtime truth and live package layout |

Supporting id, ref, persistence, and workspace references remain under
`docs/reference/`.

## Read Next

- [Current Bridge Contracts](current-bridge-contracts.md)
- [Bridge To Target Mapping](bridge-to-target-mapping.md)
- [Pipeline Stage Contracts](pipeline-stage-contracts.md)
- [Domain Ontology](domain-ontology.md)
- [Gap, Review, And Shared Attachment](gaps-and-reviews.md)
- [Reconciliation, Checkpoint, Journal, And Tax Architecture](reconciliation-tax-architecture.md)
- [Current State](../status/current-state.md)
