---
title: "Adapter Delivery Plan"
summary: "Filing-first plan for stabilizing current adapters now and deferring the broad unified adapter redesign until the Evidence And Claim Contract and the Economics Reconciliation Checkpoint Contract are stable."
doc_type: status
audience: human
owner: repo
status: active
naming_scope: forward_target
nav_order: 30
related:
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
- defer the broad unified adapter redesign until the filing path and the
  Evidence And Claim Contract and the Economics Reconciliation Checkpoint
  Contract are stable
- allow only the adapter prep work that the contract-lock pass and those
  contract pages actually need

## Work Tracks

### `now`

Filing-critical stabilization on the current adapter boundaries.

Allowed now:

- planner determinism for filing-critical adapters
- shared evidence-kind recognition and statement extraction improvements
- explicit timezone review behavior
- strict output-policy validation for filing outputs such as `cointracking_csv`
- deterministic unchanged-input verification for filing-critical adapters

Not allowed now:

- broad facet migration
- adapter-local alternate schemas for target products
- long-lived wrappers or dual-write shims

### `prep`

Narrow work that the contract-lock reset and the Evidence And Claim Contract
plus the Economics Reconciliation Checkpoint Contract need before broad adapter
redesign begins.

Allowed prep:

- bridge-to-target mapping needed for the evidence/claim contract
- adapter participation in `EvidenceSet` and `ClaimSet` emission
- shared determinism and verification helpers that remove drift in the
  evidence/claim contract

Required prep rule:

- adapter work for the evidence/claim contract must emit target products
  through the target contract pages, not adapter-local alternate schemas
- retained legacy hints needed for current drafts or facts may survive only in
  declared compatibility sidecars, not in `EvidenceSet` or
  `ClaimSet` fields

### `roadmap`

Broader unified-manifest and multi-facet migration after the filing path is
stable and those contract pages have proven the contract set.

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
- prefer shared adapter-foundation extraction over adapter-local workflow drift
- prefer explicit issues and reviews over guesswork
- do not widen the current source adapter contract during the filing window
- do not make the unified adapter redesign a hidden prerequisite for the
  Evidence And Claim Contract or the Economics Reconciliation Checkpoint
  Contract

## Filing-Critical Work To Do Now

The filing window should focus on:

- locking the actual Tier A adapter set for the active workspace
- eliminating hidden winner logic in planner-relevant adapters
- keeping statement-backed evidence deterministic where checkpoints depend on
  it
- keeping timezone handling explicit
- strengthening deterministic output validation for filing outputs
- maintaining automatic rerun-safe behavior for unchanged filing inputs

Exit criteria for the filing window:

- every filing-critical source maps to one supported adapter
- planner-enabled Tier A adapters emit stable planning files before
  translation
- unchanged filing inputs preserve expected fact, evidence, issue, and review
  behavior unless a documented product decision changes them
- `cointracking_csv` rendering remains deterministic and rejects unsupported
  shapes explicitly

## Shared-Foundation Prep

Prep work is allowed only when it materially reduces drift in the evidence/claim
contract.

Examples:

- declared bridge-to-target mapping for planner files and statement
  evidence
- shared verifiers for `EvidenceSet`, `ClaimSet`, and declared compatibility
  views
- shared comparison helpers that prove bridge outputs are reproducible from the
  authoritative target kernels

Prep work must not:

- create a second architecture center in adapter docs
- redefine target product kernels locally
- force repo-wide adapter migration before those contract pages land

## Deferred Redesign

The broader unified adapter redesign stays deferred until:

- the filing path is stable enough to trust
- the contract-lock pages are frozen
- the Evidence And Claim Contract and the Economics Reconciliation Checkpoint
  Contract have landed cleanly

At that point, use
[Unified Adapter Architecture](../concepts/unified-adapter-architecture.md) as
the contract page for broader manifest and facet work.
