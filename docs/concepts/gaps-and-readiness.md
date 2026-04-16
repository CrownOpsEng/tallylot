---
title: "Gaps And Readiness"
summary: "Owning concept page for the target gap model, review model, readiness model, sidecar rules, and shared `SubjectRef` contracts."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 45
---

Use this page when defining shared gap, review, readiness, or generic
subject-reference contracts. This document owns the target cross-stage support
model.

Current runtime note:

- the live runtime still uses stage-specific issue and review outputs such as
  `IssueRecord` and `NormalizationReviewRecord`
- those current surfaces remain current-state truth
- this page defines the target shared support model for later implementation
  slices

## Design Rules

- shared support types stay compact and stage-neutral
- explanation-heavy detail belongs in sidecars, not in hot-path kernels
- stage-owned blockers stay explicit; no stage may invent an incompatible
  blocker surface
- reviews stay advisory and must never become hidden blockers
- product-scope `ReadinessRollupRecord` rows are derived from subject-level or
  scope-level truth, not stored as the only truth
- shared support records and sidecars help stages interoperate without erasing
  stage ownership

## Provenance

Use one typed provenance model across stages.

Rules:

- provenance stays typed in runtime models
- flattening happens only at file and export boundaries
- file and member identity stay separate from row, page, or other locator
  identity
- capture identity stays separate from human-readable labels and filesystem
  paths
- shared support records and sidecars link to provenance rather than embedding
  large repeated evidence detail directly

## `SubjectRef`

Use `SubjectRef` only for shared infrastructure that needs a generic pointer.

Minimum fields:

- `subject_kind`
- `subject_id`

Supported `subject_kind` values for shared infrastructure:

- `evidence_member`
- `evidence_observation`
- `claim`
- `claim_bundle`
- `instrument`
- `location`
- `legal_owner`
- `beneficial_owner`
- `counterparty`
- `position`
- `contract`
- `economic_event`
- `economic_leg`
- `valuation`
- `checkpoint_assertion`
- `journal_entry`
- `posting`
- `basis_pool`
- `tax_input`
- `tax_output`

Rules:

- use the narrowest truthful subject kind the current stage can prove safely
- early-stage gaps and reviews may attach to evidence or claim subjects before
  business identities are fully resolved
- later-stage gaps and reviews may attach to `journal_entry`, `posting`,
  `basis_pool`, `tax_input`, or `tax_output` when that later-stage
  record is the truthful shared pointer
- use `Contract` and `Position` explicitly in business logic and modeling
- use `SubjectRef` only where shared infrastructure needs a generic pointer
- do not use `SubjectRef` as an excuse to stop modeling the true concept
- `SubjectRef` serializes, sorts, and fingerprints as
  `[subject_kind, subject_id]`

## Non-Subject Scope Ids

Non-subject scopes are allowed only when no narrower truthful subject exists.

Required scope ids:

- `selection_id`
- `claim_scope_id`
- `continuity_segment_id`
- `balance_target_id`
- `checkpoint_proposal_id`
- `product_scope_id`

Rules:

- every non-subject gap or review attachment uses one stable scope id
- `selection_id` identifies one deterministic evidence-selection
  decision boundary
- `claim_scope_id` identifies one claim-stage meaning decision
  boundary before claim-bundle selection or subject resolution is final
- `continuity_segment_id` identifies one bounded reconciliation window
- `balance_target_id` identifies one reconciliation-owned balance assertion
  target when one exact target is the truthful blocker or review scope
- `checkpoint_proposal_id` identifies one reconciliation-owned checkpoint
  proposal record before acceptance
- `product_scope_id` identifies one shared support attachment scope over one
  canonical product kernel and is not a substitute for a narrower scope
- do not attach a gap or review to `product_scope` when `subject`,
  `selection`, `claim_scope`, `continuity_segment`,
  `balance_target`, or `checkpoint_proposal` would be truthful

### `product_scope_id`

`product_scope_id` is defined once for all target support records, rollups,
projections, and sidecars.

Rules:

- `product_scope_id` is `<product_slug>:<kernel_fingerprint>`
- `product_slug` uses the lower-snake-case target product stem
- `kernel_fingerprint` is the canonical product fingerprint owned by
  [Pipeline Stage Contracts](pipeline-stage-contracts.md)
- `product_scope_id` is derived after canonical kernel fingerprinting and is not
  a product header field or a fingerprint input itself
- `product_scope_id` is never a target product id, never an upstream product
  ref, and never the primary reader key when one product id or narrower record
  id exists
- `product_scope_id` is used only for shared reporting and sidecar attachment
  when no narrower truthful subject or scope exists
- `product_scope_id` must not replace `selection_id`,
  `claim_scope_id`, `continuity_segment_id`, `balance_target_id`,
  `checkpoint_proposal_id`, or one record id when those are truthful

## Shared Stage Vocabulary

Use one stage vocabulary across gap records, review records, readiness
records, checkpoint-stage reuse, and downstream reporting.

Shared stage vocabulary:

- `evidence`
- `claim`
- `economic`
- `reconciliation`
- `checkpoint`
- `journal`
- `tax`

Rules:

- `owner_stage` and `blocking_stages` use this vocabulary
- readiness records and rollups use this vocabulary
- do not use alternate labels such as `semantic` once target-stage products
  are emitted

## Gap Model

The target shared gap model splits compact blocking truth from explanation.

### `GapRecord`

Purpose:

- compact shared blocker record used across stages

Kernel fields:

- `gap_id`
- `owner_stage`
- `blocking_stages`
- `scope_kind`
- `scope_id`
- `subject_ref`
- `gap_kind`
- `gap_key`
- `status`
- `materiality`
- `confidence`

Controlled vocabularies:

- `scope_kind`:
  - `subject`
  - `selection`
  - `claim_scope`
  - `continuity_segment`
  - `balance_target`
  - `checkpoint_proposal`
  - `product_scope`
- `gap_kind`:
  - `missing_evidence`
  - `unresolved_identity`
  - `unresolved_linkage`
  - `contradiction`
  - `policy_decision_required`
  - `manual_decision_required`
- `status`:
  - `open`
  - `resolved`
  - `superseded`
- `materiality`:
  - `material`
  - `supporting`
  - `informational`
- `confidence`:
  - `high`
  - `medium`
  - `low`

Stable ids:

- `gap_id` identifies one shared blocker record
- `gap_id` uses component array
  `[owner_stage, scope_kind, scope_key, gap_kind, gap_key]`
- `scope_key` uses the `SubjectRef` tuple when `scope_kind` is `subject`
- `scope_key` uses `scope_id` when `scope_kind` is not `subject`
- `scope_id` is required when `scope_kind` is not `subject`
- `subject_ref` is required when `scope_kind` is `subject`
- `gap_key` is the stage-owned stable discriminator for one blocking
  condition inside the declared scope

Ordering:

- sort by tuple
  `[owner_stage, scope_kind, subject_ref, scope_id, gap_kind, gap_id]`
- use JSON `null` ordering for inactive `subject_ref` and `scope_id` fields

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

- `GapRecord` is the shared blocking truth
- it stays compact enough for reducers, indexing, and hot-path references
- it must not absorb large explanatory text blobs
- `owner_stage` identifies who owns the gap semantics
- `blocking_stages` identifies who is blocked by the unresolved condition
- stages may add stage-local subtyping later, but they must not redefine the
  shared support model out of existence
- non-subject scopes must still use stable ids rather than prose labels
- `resolved` and `superseded` gaps remain valid persisted history; they are not
  deleted in place

### `GapExplanation`

Purpose:

- explanation sidecar keyed to one `GapRecord`

Fields:

- `gap_id`
- `known_facts`
- `missing_inputs`
- `possible_meanings`
- `required_evidence`
- `resolution_options`
- `next_action`
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

- explanation belongs in `GapExplanation`, not in `GapRecord`
- explanation may grow richer over time without bloating the compact blocker
  record
- stages may attach richer explanation or decision history later, but the
  common explanation shape stays recognizable across the repo

## Review Model

The target shared review model carries advisory detail without becoming a
hidden blocker surface.

### `ReviewRecord`

Purpose:

- compact shared advisory record used across stages

Kernel fields:

- `review_id`
- `owner_stage`
- `scope_kind`
- `scope_id`
- `subject_ref`
- `review_kind`
- `review_key`
- `status`
- `confidence`
- `gap_ids`

Controlled vocabularies:

- `scope_kind`:
  - `subject`
  - `selection`
  - `claim_scope`
  - `continuity_segment`
  - `balance_target`
  - `checkpoint_proposal`
  - `product_scope`
- `status`:
  - `open`
  - `acknowledged`
  - `resolved`
  - `superseded`
- `confidence`:
  - `high`
  - `medium`
  - `low`

Stable ids:

- `review_id` identifies one advisory record
- `review_id` uses component array
  `[owner_stage, scope_kind, scope_key, review_kind, review_key]`
- `scope_key` uses the `SubjectRef` tuple when `scope_kind` is `subject`
- `scope_key` uses `scope_id` when `scope_kind` is not `subject`
- `review_kind` is the owner-stage stable advisory label for one review family
- `review_key` is the owner-stage stable discriminator for one advisory
  observation inside the declared scope

Ordering:

- sort by tuple
  `[owner_stage, scope_kind, subject_ref, scope_id, review_kind, review_id]`
- use JSON `null` ordering for inactive `subject_ref` and `scope_id` fields
- sort `gap_ids` lexicographically

Serialization:

- serialize review kernel records only
- use stable object-key ordering
- preserve the declared review order above

Fingerprint inputs:

- review records in canonical order
- `schema_version`
- sorted `gap_ids`

Rules:

- reviews are advisory only
- reviews use the same scope attachment scheme as gaps
- reviews never block on their own
- a review may coexist with a paired gap on the same subject or scope
- shared review records must not become a second blocker model in disguise

### `ReviewExplanation`

Purpose:

- explanation sidecar keyed to one `ReviewRecord`

Fields:

- `review_id`
- `headline`
- `known_facts`
- `follow_up`
- `provenance_refs`

Ordering:

- sort by `review_id`
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
- `review_id`
- sorted `provenance_refs`

Rules:

- explanation belongs in `ReviewExplanation`, not in `ReviewRecord`
- review explanation may become richer over time without changing the advisory
  record

## Readiness Model

Readiness is subject-first, stage-specific, and reducible into canonical
rollups plus derived reports.

### `ReadinessStatus`

Shared status vocabulary:

- `ready`
- `blocked`
- `partial`
- `not_applicable`

`partial` means:

- some required meanings or assertions resolved
- at least one blocking gap still open
- the remaining uncertainty is recorded through gap ids, not prose-only
  explanation

### `ReadinessRecord`

Purpose:

- stage-specific readiness for one `SubjectRef`

Kernel fields:

- `readiness_id`
- `subject_ref`
- `stage`
- `status`
- `blocking_gap_ids`

Stable ids:

- `readiness_id` identifies one readiness record for one subject and
  one stage
- `readiness_id` uses component array `[subject_ref, stage]`

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
  completeness before claim commitment
- reducers work from subject readiness plus gaps, not from hand-built
  `ReadinessRollupRecord` rows
- a subject may be ready for one stage and blocked for another
- readiness points to blocking gap ids rather than hiding blockers in
  explanation text

### `ReadinessRollupRecord`

Purpose:

- derived readiness rollup over subject readiness

Fields:

- `readiness_rollup_id`
- `stage`
- `rollup_kind`
- `rollup_key`
- `status`
- `blocking_gap_ids`
- `ready_count`
- `partial_count`
- `blocked_count`
- `not_applicable_count`

Controlled `rollup_kind` vocabulary:

- `location`
- `instrument`
- `continuity_segment`
- `as_of`
- `tax_year`
- `product_scope`

Rollup-key rules:

- `location` uses one `location_id`
- `instrument` uses one `instrument_id`
- `continuity_segment` uses one `continuity_segment_id`
- `as_of` uses one canonical `YYYY-MM-DD` date string
- `tax_year` uses one integer tax year
- `product_scope` uses one `product_scope_id`

Stable ids:

- `readiness_rollup_id` identifies one derived readiness rollup record
- `readiness_rollup_id` uses component array
  `[stage, rollup_kind, rollup_key]`

Ordering:

- sort by tuple `[stage, rollup_kind, rollup_key]`
- sort `blocking_gap_ids` lexicographically

Serialization:

- serialize readiness rollup records only
- use stable object-key ordering
- preserve the declared readiness rollup order above

Fingerprint inputs:

- readiness rollup records in canonical order
- `schema_version`
- sorted `blocking_gap_ids`
- the ordered `ReadinessRecord` ids that fed the rollup

Rules:

- `ReadinessRollupRecord` rows are derived output, not the only stored truth
- `partial` requires at least one resolved assertion plus at least one open
  blocking gap id
- if no required assertion has resolved yet, status is `blocked`, not
  `partial`
- if no blocker applies, status is `ready`, not `partial`
- product-scope `ReadinessRollupRecord` rows remain reproducible from ordered
  readiness and gap records without manual status editing
- canonical rollup kinds stay stage- and domain-oriented rather than grouping
  by source identity
- source-grouped operator views belong in derived reports or compatibility
  projections rather than in `ReadinessRollupRecord.rollup_kind`
- stages use only the dimensions they actually own or can derive safely

## Bridge Mapping From Issue And Review Records

The live bridge still emits `IssueRecord` and `NormalizationReviewRecord`.

Mapping rules:

- a blocking `IssueRecord` maps to one `GapRecord` plus one `GapExplanation`
  when owner stage, blocking stages, scope, and blocker semantics align
- `IssueRecord.kind`, `severity`, `context_timestamp`, and typed provenance are
  gap inputs, not free text to reinterpret later
- `NormalizationReviewRecord` maps to one `ReviewRecord` plus one
  `ReviewExplanation` when owner stage, scope, and advisory meaning align
- when one factual cause produces both a blocker and an advisory review, the
  blocker lands in `GapRecord` and the review remains keyed sidecar detail
- current bridge ids remain traceable when later stages adopt target-native gap
  or review ids

## Anti-Duplication And Sidecar Rules

Copy only when meaning changes.

Meaning:

- one stage owns one meaning surface
- downstream stages reference upstream records by stable ids or product ids
- `product_scope_id` is allowed only for shared reporting and sidecar attachment
  when no narrower truthful product id, scope id, or record id exists
- downstream stages add stage-owned outputs only

Keep these first-class:

- evidence members
- evidence observations
- claims and claim bundles
- economic events
- economic legs
- valuations
- identities and refs
- ownership state
- settlement status and lifecycle events
- `CheckpointAssertion` truth
- postings
- tax inputs and outputs

Use sidecars only for:

- provenance
- gaps
- reviews
- readiness
- annotations
- comparison traces
- policy explanations

Sidecars must never become:

- the only real copy of business meaning
- a substitute for unresolved business concepts
- a junk drawer of unresolved text

Performance implication:

- avoiding meaning duplication is also a performance rule
- repeated full detail copies increase read amplification, join cost, and drift
  risk
- the correct shape is stable ids or product ids plus stage-owned deltas, with
  `product_scope_id` reserved for shared reporting or sidecar attachment only

## Current-To-Target Boundary

- current `IssueRecord` and `NormalizationReviewRecord` remain live bridge
  outputs today
- later implementation may map current bridge issues and reviews into the
  target support model where stage ownership and meaning line up
- current-state docs keep current issue and review names where accuracy
  requires them
