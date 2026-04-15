---
title: "Adapter Delivery Plan"
summary: "Filing-first plan for stabilizing current adapters now and deferring the broad unified adapter redesign until the filing path and bounded first slices are stable."
doc_type: status
audience: human
owner: repo
status: active
nav_order: 30
related:
  - ROADMAP.md
  - docs/guides/write-an-adapter.md
  - docs/concepts/unified-adapter-architecture.md
  - docs/concepts/bridge-to-target-mapping.md
  - docs/concepts/pipeline-stage-contracts.md
  - docs/status/current-state.md
---

Use this plan when deciding whether adapter work belongs in the current
filing-critical window or in the later unified-adapter redesign.

## Decision

The repo uses a filing-first adapter strategy:

- harden the current adapter path where it directly reduces filing risk
- defer the broad unified adapter redesign until the filing path and bounded
  first slices are stable
- allow only the adapter prep work that the contract-lock pass and first slices
  actually need

## Work Tracks

### `now`

Filing-critical stabilization on the current adapter boundaries.

Allowed now:

- planner determinism for filing-critical adapters
- shared family recognition and statement extraction improvements
- explicit timezone review behavior
- strict output-policy validation for filing outputs such as `cointracking_csv`
- replay-grade verification for unchanged filing inputs

Not allowed now:

- broad facet migration
- adapter-local alternate schemas for target products
- long-lived wrappers or dual-write shims

### `prep`

Narrow work that Phase 0 and the first bounded slices need before broad
adapter redesign begins.

Allowed prep:

- bridge-to-target mapping needed for the first slice
- adapter participation in canonical `EvidenceSet` and `ClaimSet` emission
- shared determinism and verification helpers that remove first-slice drift

Required prep rule:

- first-slice adapter work must emit target products through the canonical
  owner docs, not adapter-local alternate schemas
- retained legacy hints needed for current drafts or facts may survive only in
  declared compatibility sidecars, not in canonical `EvidenceSet` or
  `ClaimSet` fields

### `roadmap`

Broader unified-manifest and multi-facet migration after the filing path is
stable and the first bounded slices have proven the contract set.

## Priority Tiers

| Tier | Meaning | Action in this plan |
| --- | --- | --- |
| Tier A | Required for the active filing workspace or filing output path | Harden now. |
| Tier B | Supported but not filing-critical in the active window | Touch only when a shared fix improves it cheaply. |
| Tier C | Stubbed, reserved, or clearly non-filing | Do not expand now. |

The actual Tier A set comes from the active external workspace, not from
in-repo guesswork.

## Filing-Window Rules

- prefer deterministic current behavior over ambitious interface redesign
- prefer shared support extraction over adapter-local workflow drift
- prefer explicit issues and reviews over guesswork
- do not widen the current source adapter contract during the filing window
- do not make the unified adapter redesign a hidden prerequisite for the first
  bounded slices

## Filing-Critical Work To Do Now

The filing window should focus on:

- locking the actual Tier A adapter set for the active workspace
- eliminating hidden winner logic in planner-relevant adapters
- keeping statement-backed evidence deterministic where checkpoints depend on
  it
- keeping timezone handling explicit
- strengthening deterministic output validation for filing outputs
- maintaining replay-grade verification for unchanged inputs

Exit criteria for the filing window:

- every filing-critical source maps to one supported adapter
- planner-enabled Tier A adapters emit stable planning artifacts before
  translation
- unchanged filing inputs preserve expected fact, evidence, issue, and review
  behavior unless a documented product decision changes them
- `cointracking_csv` rendering remains deterministic and rejects unsupported
  shapes explicitly

## Shared-Foundation Prep

Prep work is allowed only when it materially reduces first-slice drift.

Examples:

- canonical bridge-to-target mapping for planner artifacts and statement
  evidence
- shared verifiers for `EvidenceSet`, `ClaimSet`, and declared compatibility
  projections
- shared comparison helpers that prove bridge outputs are reproducible from the
  authoritative target kernels

Prep work must not:

- create a second architecture center in adapter docs
- redefine target product kernels locally
- force repo-wide family migration before the bounded slices land

## Deferred Redesign

The broader unified adapter redesign stays deferred until:

- the filing path is stable enough to trust
- the contract-lock owner docs are frozen
- the first upstream and downstream bounded slices have landed cleanly

At that point, use
[Unified Adapter Architecture](../concepts/unified-adapter-architecture.md) as
the design anchor for broader manifest and facet work.
