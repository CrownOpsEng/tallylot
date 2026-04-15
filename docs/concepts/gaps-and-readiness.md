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

- shared support types stay compact and stage-neutral
- explanation-heavy payloads belong in sidecars, not in the hot-path core
- stage-owned blockers stay explicit; no stage may invent an incompatible
  blocker surface
- dataset summaries are derived from subject-level truth, not stored as the
  only truth
- shared support structures help stages interoperate without erasing stage
  ownership

## Provenance

Use one typed provenance model across stages.

Rules:

- provenance stays typed in runtime models
- flattening happens only at artifact and export boundaries
- file and member identity stay separate from row, page, or anchor identity
- capture identity stays separate from human-readable labels and file-system
  paths
- shared support models link to provenance rather than embedding large repeated
  evidence payloads directly

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
- `SubjectRef` serializes, sorts, and fingerprints as
  `[subject_kind, subject_id]`

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

## Shared Stage Vocabulary

Use one stage vocabulary across gaps, readiness, checkpoint reuse, and
downstream reporting.

Shared stage vocabulary:

- `evidence`
- `claim`
- `economic`
- `reconciliation`
- `checkpoint`
- `accounting`
- `tax`

Rules:

- `owner_stage` and `blocking_stages` use this vocabulary
- readiness records and projections use this vocabulary
- do not use alternate labels such as `semantic` once target-stage artifacts
  are emitted

## Gap Model

The target shared gap model splits compact blocking truth from explanation.

### `GapCore`

Purpose:

- compact shared blocker record used across stages

Kernel fields:

- `gap_id`
- `owner_stage`
- `blocking_stages`
- `scope_kind`
- `scope_id_or_null`
- `subject_ref_or_null`
- `gap_kind`
- `gap_anchor`
- `status`
- `materiality`
- `confidence`

Controlled vocabularies:

- `scope_kind`:
  - `subject`
  - `selection_group`
  - `continuity_segment`
  - `checkpoint_candidate`
  - `dataset`
- `gap_kind`:
  - `missing_evidence`
  - `unresolved_identity`
  - `unresolved_linkage`
  - `contradiction`
  - `policy_required_determination`
  - `operator_override_required`
- `status`:
  - `open`
  - `resolved`
  - `superseded`
- `materiality`:
  - `material`
  - `contextual`
  - `informational`
- `confidence`:
  - `high`
  - `medium`
  - `low`

Stable ids:

- `gap_id` identifies one shared blocker record
- `gap_id` uses component array
  `[owner_stage, scope_kind, scope_anchor, gap_kind, gap_anchor]`
- `scope_anchor` uses the `SubjectRef` tuple when `scope_kind` is `subject`
- `scope_anchor` uses `scope_id_or_null` when `scope_kind` is not `subject`
- `scope_id_or_null` is required when `scope_kind` is not `subject`
- `subject_ref_or_null` is required when `scope_kind` is `subject`
- `gap_anchor` is the stage-owned stable discriminator for one blocking
  condition inside the declared scope

Ordering:

- sort by tuple
  `[owner_stage, scope_kind, subject_ref_or_null, scope_id_or_null, gap_kind, gap_id]`
- use JSON `null` ordering for `subject_ref_or_null` and `scope_id_or_null`
  when one field is not applicable

Serialization:

- serialize kernel records only
- use stable object-key ordering
- preserve the declared gap order above
- sort `blocking_stages` in canonical stage order

Fingerprint inputs:

- kernel records in canonical order
- `schema_version`
- sorted `blocking_stages`

Rules:

- `GapCore` is the shared blocking truth
- it stays compact enough for reducers, indexing, and hot-path references
- it must not absorb large explanatory text blobs
- `owner_stage` identifies who owns the gap semantics
- `blocking_stages` identifies who is blocked by the unresolved condition
- stages may add stage-local subtyping later, but they must not redefine the
  shared core out of existence
- non-subject scopes must still use stable ids rather than prose labels
- `resolved` and `superseded` gaps remain valid persisted history; they are not
  deleted in place

### `GapExplanation`

Purpose:

- explanation sidecar keyed to one `GapCore`

Fields:

- `gap_id`
- `known_facts`
- `missing_inputs`
- `candidate_interpretations`
- `required_evidence`
- `allowed_resolution_methods`
- `recommended_next_action`
- `provenance_refs`

Ordering:

- sort by `gap_id`
- preserve list order inside one explanation field when the owning stage has a
  meaningful canonical order

Serialization:

- serialize explanation records only
- use stable object-key ordering
- preserve the declared explanation order above
- sort `provenance_refs` when the stage does not declare a stronger order

Fingerprint inputs:

- explanation records in canonical order
- `schema_version`
- `gap_id`
- sorted `provenance_refs`

Rules:

- explanation belongs in `GapExplanation`, not in `GapCore`
- explanation may grow richer over time without bloating the compact blocker
  record
- stages may attach richer explanation or decision history later, but the
  common explanation shape stays recognizable across the repo

## Readiness Model

Readiness is subject-first, stage-specific, and reducible into reporting
projections.

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

Kernel fields:

- `subject_ref`
- `stage`
- `status`
- `blocking_gap_ids`

Stable ids:

- `subject_readiness_id` identifies one readiness record for one subject and
  one stage
- `subject_readiness_id` uses component array `[subject_ref, stage]`

Ordering:

- sort by tuple `[stage, subject_ref.subject_kind, subject_ref.subject_id]`
- sort `blocking_gap_ids` lexicographically

Serialization:

- serialize readiness records only
- use stable object-key ordering
- preserve the declared readiness order above

Fingerprint inputs:

- readiness records in canonical order
- `schema_version`
- sorted `blocking_gap_ids`

Rules:

- subject readiness is the base truth
- `evidence` readiness covers deterministic evidence selection and observation
  completeness before semantic commitment
- reducers work from subject readiness plus gaps, not from hand-built whole
  dataset statuses
- a subject may be ready for one stage and blocked for another
- readiness points to blocking gap ids rather than hiding blockers in summary
  text

### `ReadinessProjection`

Purpose:

- derived reporting view over subject readiness

Fields:

- `projection_id`
- `stage`
- `projection_dimension`
- `projection_key`
- `status`
- `blocking_gap_ids`
- `ready_subject_count`
- `partial_subject_count`
- `blocked_subject_count`
- `not_applicable_subject_count`

Controlled `projection_dimension` vocabulary:

- `source`
- `location`
- `instrument`
- `continuity_segment`
- `checkpoint_date`
- `tax_year`
- `dataset`

Projection-key rules:

- `source` uses the source string
- `location` uses one `location_id`
- `instrument` uses one `instrument_id`
- `continuity_segment` uses one `continuity_segment_id`
- `checkpoint_date` uses one canonical `YYYY-MM-DD` date string
- `tax_year` uses one integer tax year
- `dataset` uses one `dataset_id`

Stable ids:

- `projection_id` identifies one derived readiness projection
- `projection_id` uses component array
  `[stage, projection_dimension, projection_key]`

Ordering:

- sort by tuple `[stage, projection_dimension, projection_key]`
- sort `blocking_gap_ids` lexicographically

Serialization:

- serialize projection records only
- use stable object-key ordering
- preserve the declared projection order above

Fingerprint inputs:

- projection records in canonical order
- `schema_version`
- sorted `blocking_gap_ids`
- the ordered `SubjectReadinessRecord` ids that fed the projection

Rules:

- projections are derived output, not the only stored truth
- `partial` requires at least one resolved assertion plus at least one open
  blocking gap id
- if no required assertion has resolved yet, status is `blocked`, not
  `partial`
- if no blocker applies, status is `ready`, not `partial`
- dataset summaries remain reproducible from ordered readiness and gap records
  without manual status editing
- stages use only the dimensions they actually own or can derive safely

## Shared Checkpoint Assertions

Use one shared checkpoint-assertion vocabulary across reconciliation,
checkpoints, accounting, and tax.

Rules:

- checkpoint assertions stay first-class and referenceable
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
- current bridge ids remain traceable when later stages adopt target-native gap
  or review ids

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
- current-state docs keep current issue and review names where accuracy
  requires them
