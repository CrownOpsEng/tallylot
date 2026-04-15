---
title: "Gaps And Readiness"
summary: "Owning concept page for the target gap model, readiness model, sidecar rules, and shared `SubjectRef` contracts."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 45
---

Use this page when defining shared blocker, readiness, or generic
subject-reference contracts. This document owns the target cross-stage gap and
readiness model.

Current runtime note:

- the live runtime still uses stage-specific issue and review artifacts such as
  `IssueRecord` and `NormalizationReviewRecord`
- those current surfaces remain current-state truth
- this page defines the target shared support model for later implementation
  slices

## Design Rules

- shared support types should stay compact and stage-neutral
- explanation-heavy payloads belong in sidecars, not in the hot-path core
- stage-owned blockers stay explicit; no stage should invent an incompatible
  blocker surface
- dataset summaries are derived from subject-level truth, not stored as the
  only truth
- shared support structures should help stages interoperate without erasing
  stage ownership

## Provenance

Use one typed provenance model across stages.

Rules:

- provenance stays typed in runtime models
- flattening happens only at artifact and export boundaries
- file and member identity stay separate from row, page, or anchor identity
- capture identity stays separate from human-readable labels and file-system
  paths
- shared support models should link to provenance rather than embedding large
  repeated evidence payloads directly

## `SubjectRef`

Use `SubjectRef` only for shared infrastructure that needs a generic pointer.

Minimum fields:

- `subject_kind`
- `subject_id`

Supported `subject_kind` values for shared infrastructure:

- `evidence_member`
- `evidence_record`
- `claim`
- `instrument`
- `location`
- `legal_owner`
- `beneficial_owner`
- `counterparty`
- `position`
- `contract`
- `economic_event`
- `checkpoint_assertion`

Rules:

- use the narrowest truthful subject kind the current stage can prove safely
- early-stage gaps may attach to evidence or claim subjects before business
  identities are fully resolved
- use `Contract` and `Position` explicitly in business logic and modeling
- use `SubjectRef` only where shared infrastructure needs a generic pointer
- do not use `SubjectRef` as an excuse to stop modeling the true concept

## Non-Subject Scope Identity

Non-subject scopes are allowed only when no narrower truthful subject exists.

Required scope ids:

- `selection_group_id`
- `continuity_segment_id`
- `checkpoint_candidate_id`
- `dataset_id`

Rules:

- every non-subject gap attachment uses one stable scope id
- `selection_group_id` identifies one deterministic evidence-selection
  decision boundary
- `continuity_segment_id` identifies one bounded reconciliation window
- `checkpoint_candidate_id` identifies one reconciliation-owned checkpoint
  proposal before acceptance
- `dataset_id` identifies one persisted stage kernel or one explicit slice-wide
  dataset under review
- do not attach a gap to `dataset` scope when `subject`, `selection_group`, or
  `checkpoint_candidate` would be truthful

## Gap Model

The target shared gap model splits compact blocking truth from explanation.

### `GapCore`

Purpose:

- compact shared blocker record used across stages

Minimum fields:

- `gap_id`
- `owner_stage`
- `blocking_stages`
- `scope_kind`
- `gap_kind`
- `status`
- `materiality`
- `confidence`
- `subject_ref` when `scope_kind` is `subject`

Rules:

- `scope_kind` is the attachment contract for the gap core
- supported `scope_kind` values are:
  - `subject`
  - `selection_group`
  - `continuity_segment`
  - `checkpoint_candidate`
  - `dataset`
- use `subject_ref` whenever one truthful subject exists
- use non-subject scope kinds only when no narrower truthful subject exists
- `GapCore` is the shared blocking truth
- it stays compact enough for reducers, indexing, and hot-path references
- it must not absorb large explanatory text blobs
- `owner_stage` identifies who owns the gap semantics
- `blocking_stages` identifies who is blocked by the unresolved condition
- later stages may add stage-local subtyping, but they should not redefine the
  shared core out of existence
- non-subject scopes must still use stable ids rather than prose labels

### `GapExplanation`

Purpose:

- explanation sidecar keyed to one `GapCore`

Minimum fields:

- `gap_id`
- `known_facts`
- `missing_inputs`
- `candidate_interpretations`
- `required_evidence`
- `allowed_resolution_methods`
- `recommended_next_action`
- `provenance_refs`

Rules:

- explanation belongs in `GapExplanation`, not in `GapCore`
- explanation may grow richer over time without bloating the compact shared
  blocker record
- stages may attach richer explanation or decision history later, but the
  common explanation shape should stay recognizable across the repo

### Minimum Gap Taxonomy

- `missing_evidence`
- `unresolved_identity`
- `unresolved_linkage`
- `contradiction`
- `policy_required_determination`
- `operator_override_required`

Rules:

- gap ownership stays explicit by stage
- accounting-owned gaps, reconciliation-owned gaps, checkpoint-owned gaps, and
  tax-owned gaps must not be conflated operationally
- stages may add stage-local subtyping later, but not by replacing the shared
  taxonomy completely
- materiality and confidence should remain first-class attributes on the gap
  core, not only free-text explanation details

## Readiness Model

Readiness is subject-first, stage-specific, and reducible into reporting
projections.

### `ReadinessStage`

Shared stage vocabulary:

- `evidence`
- `semantic`
- `reconciliation`
- `checkpoint`
- `accounting`
- `tax`

### `ReadinessStatus`

Shared status vocabulary:

- `ready`
- `blocked`
- `partial`
- `not_applicable`

`partial` means:

- some required interpretations or assertions resolved
- at least one blocking gap still open
- the remaining uncertainty is recorded through gap ids, not prose-only summary

### `SubjectReadinessRecord`

Purpose:

- stage-specific readiness for one `SubjectRef`

Minimum fields:

- `subject_ref`
- `stage`
- `status`
- `blocking_gap_ids`

Optional derived context may include:

- confidence
- materiality
- provenance or explanation references

Rules:

- subject readiness is the base truth
- `evidence` readiness covers deterministic evidence selection and observation
  completeness before semantic commitment
- reducers should work from subject readiness plus gaps, not from hand-built
  whole-dataset statuses
- a subject may be ready for one stage and blocked for another
- readiness should point to blocking gap ids rather than hiding blockers in
  summary text

## Reducer Rules

Readiness reducers should remain compact, deterministic, and subject-first.

Rules:

- reducers work from `GapCore`, stable scope ids, and subject readiness records
- reducers must not infer readiness from explanation prose
- reducers may roll up from subject truth into reporting projections, but the
  projection is derived output, not the only stored truth
- `partial` readiness requires at least one resolved assertion plus at least
  one open blocking gap id
- if no required assertion has resolved yet, status is `blocked`, not `partial`
- if no blocker applies, status is `ready`, not `partial`
- dataset summaries should be reproducible from ordered readiness and gap
  records without manual status editing

### `ReadinessProjection`

Purpose:

- derived reporting view over subject readiness

Allowed optional projection dimensions:

- source
- location
- instrument
- continuity segment
- checkpoint date
- tax year

Rules:

- these are reporting and recalculation dimensions, not mandatory keys on
  every readiness record
- a stage should use only the dimensions it actually owns or can derive
  safely
- do not turn readiness into a mandatory global cube just to satisfy one
  report

## Shared Checkpoint Assertions

Use one shared checkpoint-assertion vocabulary across reconciliation,
checkpoints, accounting, and tax.

Rules:

- checkpoint assertions should stay first-class and referenceable
- downstream stages may reuse them, but should not redefine them into
  incompatible local variants

## Bridge Mapping From Issue And Review Records

The live bridge still emits `IssueRecord` and `NormalizationReviewRecord`.

Mapping rules:

- a blocking `IssueRecord` maps to one `GapCore` plus one `GapExplanation`
  when owner stage, blocking stages, scope, and blocker semantics align
- `IssueRecord.kind`, `severity`, `context_timestamp`, and typed provenance are
  gap inputs, not free text to reinterpret later
- `NormalizationReviewRecord` remains a review sidecar unless a paired
  blocking condition also exists
- when one factual cause produces both a blocker and an advisory review, the
  blocker lands in `GapCore` and the review remains keyed sidecar context
- current bridge ids should remain traceable when later stages adopt
  target-native gap or review ids

## Anti-Duplication And Sidecar Rules

Copy only when meaning changes.

Meaning:

- one stage owns one semantic payload
- downstream stages reference upstream records by stable ids
- downstream stages add stage-owned outputs only

Keep these first-class:

- economic events
- economic legs
- identities
- ownership state
- settlement and lifecycle state
- valuations
- checkpoint assertions
- postings
- tax inputs

Use sidecars only for:

- provenance
- gaps
- readiness
- reviews
- annotations
- comparison traces
- policy explanations

Sidecars must never become:

- the only real copy of business meaning
- a substitute for missing entities
- a junk drawer of unresolved text

Performance implication:

- avoiding semantic duplication is also a performance rule
- repeated full payloads increase read amplification, join cost, and drift risk
- the correct shape is stable ids plus stage-owned deltas

## Current-to-Target Boundary

- current `IssueRecord` and `NormalizationReviewRecord` remain live bridge
  outputs today
- later implementation may map current bridge issues and reviews into the
  target gap/readiness model where the stage ownership and semantics line up
- current-state docs should keep current issue and review names where accuracy
  requires them
