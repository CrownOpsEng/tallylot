---
title: "Unified Adapter Architecture"
summary: "Forward design for the future adapter manifest, facets, and verification model without re-owning target product contracts."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 60
related:
  - ROADMAP.md
  - docs/status/adapter-delivery-plan.md
  - docs/guides/write-an-adapter.md
  - docs/concepts/bridge-to-target-mapping.md
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/domain-ontology.md
  - docs/concepts/reconciliation-tax-architecture.md
---

Read this document before shaping large adapter-design work. Use it as the
forward design anchor for manifests, facets, and deterministic verification.
This page does not own target product record families, ids, fingerprints, or
taxonomy details. Those stay with the owner pages.

## Scope And Precedence

Owner-page precedence:

- [Pipeline Stage Contracts](pipeline-stage-contracts.md) owns target product
  kernels, ids, ordering, and fingerprints
- [Domain Ontology](domain-ontology.md) owns entity and ref seams
- [Bridge To Target Mapping](bridge-to-target-mapping.md) owns migration
  cutovers and compatibility projections
- [Reconciliation And Tax Architecture](reconciliation-tax-architecture.md)
  owns persistence, partitioning, and fast-path rules
- this page owns only adapter responsibilities, manifest direction, facet
  design, and adapter verification posture

## Design Direction

The future adapter architecture should unify around:

- one manifest model
- a small set of purpose-defined facets
- deterministic adapter products that map into the target runtime pipeline
- one shared verification model

It should not unify around:

- one monolithic source-adapter interface
- adapter-local target schemas
- a second architecture center beside the target runtime pipeline
- indefinite bridge wrappers or dual-contract shims

## Adapter Responsibility Boundary

Adapters own adapter-local work only.

Reader-side examples:

- recognizing adapter-specific evidence kinds
- parsing adapter-specific files and documents
- mapping adapter fields into evidence-local claims
- surfacing evidence-local ambiguity, precision, or unsupported cases

Writer-side examples:

- mapping accepted upstream truth into output-specific row models
- applying target-specific formatting and validation rules

Shared runtime owns cross-adapter workflow:

- evidence selection and candidate comparison
- stable ordering and fingerprints
- shared issue, review, and readiness conventions
- economic compilation
- bridge compatibility projection generation
- replay and parity verification
- output packaging

If two adapters need the same rule and the rule is not adapter-specific, it
belongs in shared runtime services rather than duplicated adapter logic.

## Manifest Direction

Every future adapter should publish one manifest that answers:

- what evidence files, projections, or rendered packages it reads or writes
- which facets it implements
- which determinism guarantees it provides
- which compatibility window and schema versions it supports
- which unsupported or review-worthy surfaces it declares

The manifest is the durable declaration. Facets are the executable behaviors
attached to that declaration.

## Facet Model

Use a small set of purpose-defined facets rather than one giant contract.

| Facet | Purpose |
| --- | --- |
| `DiscoveryFacet` | Discover evidence and describe route, kind, or confidence hints. |
| `EvidenceFacet` | Read selected evidence and emit `EvidenceSet`-aligned outputs. |
| `StatementFacet` | Recognize and parse statement documents plus statement-specific evidence detail. |
| `ClaimFacet` | Emit evidence-local claim meaning that maps into `ClaimSet`. |
| `RenderFacet` | Emit rendered files or external packages from accepted upstream truth. |

Portfolio behavior is not a separate species. It is evidence-reading behavior
that emits position or balance meaning instead of activity-heavy claim sets.

## Deterministic Verification Model

Adapter verification must be a written contract, not a best-effort habit.

Required verification properties:

- unchanged inputs preserve declared evidence-kind recognition
- unchanged inputs preserve declared ordering and fingerprints
- unsupported or ambiguous cases surface explicitly
- compatibility projections remain reproducible from authoritative target
  kernels during migration
- output adapters reject unsupported upstream shapes before serialization

Verification should center on adapter products and shared projections, not on
adapter-local shell choreography.

## Migration Posture

The unified adapter redesign remains deferred until the filing-critical path and
current first slices are stable.

Rules during the current migration window:

- adapter work for the current first slice must emit target products through the canonical
  owner pages, not adapter-local alternate schemas
- adapters may emit declared compatibility sidecars for retained legacy
  draft-or-fact reproduction during migration, but canonical target kernels
  stay limited to target meaning
- adapter docs may describe how adapters participate in `EvidenceSet`,
  `ClaimSet`, and compatibility projections, but they may not redefine those
  products
- the current first slice must not depend on a repo-wide facet migration
- `SourceTranslationBatch` remains honest current-state truth until its bounded
  replacement slice lands

Use [Adapter Delivery Plan](../status/adapter-delivery-plan.md) for timing and
priority decisions. Use this page only for the future adapter shape once that
work becomes active.
