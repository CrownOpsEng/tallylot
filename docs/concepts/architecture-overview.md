---
title: "Architecture Overview"
summary: "High-level map of the current bridge, the target pipeline, and the focused pages that own each major contract."
doc_type: concept
audience: human
owner: repo
status: active
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

The owner pages freeze product ids, product headers, critical-path kernel field
tables, and the compatibility sidecar boundary for retained legacy
hint fields.

## Layer Shape

- `domain/` owns business models, refs, enums, and value objects
- `application/` owns use-case orchestration over domain models and ports
- `ports/` defines narrow typed boundaries
- `infrastructure/` implements ports
- `adapters/` translates source and output formats
- `interfaces/` exposes CLI entry points over application capabilities

Raw evidence and live workspace files remain in the external workspace, not
in the repo.

## Contract Map

Use these pages as the primary owners:

| Page | Owns |
| --- | --- |
| [Current Bridge Contracts](current-bridge-contracts.md) | live bridge truth and bridge surface rules |
| [Bridge To Target Mapping](bridge-to-target-mapping.md) | authoritative writer rules, compatibility views, and reader cutovers |
| [Pipeline Stage Contracts](pipeline-stage-contracts.md) | target product kernels, ids, ordering, and handoff rules |
| [Domain Ontology](domain-ontology.md) | identity seams, ref recipes, and package ownership |
| [Gaps And Readiness](gaps-and-readiness.md) | gap, review, and readiness contracts plus `SubjectRef` |
| [Reconciliation And Tax Architecture](reconciliation-tax-architecture.md) | trust gates, persistence, partitioning, and fast-path rules |
| [First Upstream Slice Contract](../reference/first-upstream-slice-contract.md) | first upstream `EvidenceSet -> ClaimSet` slice |
| [First Downstream Slice Contract](../reference/first-downstream-slice-contract.md) | first downstream `EconomicFacts -> ReconciliationState -> Checkpoint` slice |
| [ROADMAP.md](../../ROADMAP.md) | sequencing, gating, and rollout phases |
| [Current State](../status/current-state.md) | implemented runtime truth and live package layout |

Non-owning helper references remain under
`docs/reference/`.

## Read Next

- [Current Bridge Contracts](current-bridge-contracts.md)
- [Bridge To Target Mapping](bridge-to-target-mapping.md)
- [Pipeline Stage Contracts](pipeline-stage-contracts.md)
- [Domain Ontology](domain-ontology.md)
- [Gaps And Readiness](gaps-and-readiness.md)
- [Reconciliation And Tax Architecture](reconciliation-tax-architecture.md)
- [Current State](../status/current-state.md)
