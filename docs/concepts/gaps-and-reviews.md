---
title: "Gap, Review, And Shared Attachment"
summary: "Shared gap, review, sidecar, `SubjectRef`, and shared attachment contracts for the target pipeline."
doc_type: concept
audience: human
owner: repo
status: active
naming_scope: forward_target
nav_order: 45
---

Use this page when defining shared gap, review, `SubjectRef`, or shared
attachment contracts. This page defines the target cross-stage gap, review,
generic subject-attachment, and shared scope-attachment model.

## Design Rules

- gap and review records stay compact and stage-neutral
- explanation-heavy detail belongs in sidecars, not in hot-path kernels
- stage-owned blockers stay explicit; no stage may invent an incompatible
  blocker surface
- reviews stay advisory and must never become hidden blockers
- readiness is a capability-owned derived view, not a shared canonical record
  family
- grouped readiness stays on capability-owned derived outputs, not on a shared
  assessment family
- shared gap and review records plus sidecars help stages interoperate without
  erasing stage ownership

## Provenance

Use one typed provenance model across stages.

Rules:

- provenance stays typed in runtime models
- flattening happens only at file and export boundaries
- file and member identity stay separate from row, page, or other locator
  identity
- capture identity stays separate from human-readable labels and filesystem
  paths
- gap and review records and sidecars link to provenance rather than embedding
  large repeated evidence detail directly

## `SubjectRef`

Use `SubjectRef` only for shared infrastructure that needs a generic pointer.

Minimum fields:

- `subject_kind`
- `subject_key`

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
- `subject_key` may hold either one stable record id or one canonical ref tuple,
  depending on the `subject_kind`
- `SubjectRef` serializes, sorts, and fingerprints as
  `[subject_kind, subject_key]`

## Non-Subject Scope Ids

Non-subject scopes are allowed only when no narrower truthful subject exists.

Required scope ids:

- `selection_id`
- `claim_scope_id`
- `continuity_segment_id`
- `balance_target_id`
- `checkpoint_proposal_id`
- `kernel_scope_id`

Rules:

- every non-subject gap or review attachment uses one stable scope id
- `selection_id` identifies one deterministic evidence-selection
  decision boundary
- `claim_scope_id` identifies one claim-stage meaning decision
  boundary before claim-bundle decisions or subject resolution are final
- `continuity_segment_id` identifies one bounded reconciliation window
- `balance_target_id` identifies one reconciliation-owned balance assertion
  target when one exact target is the truthful blocker or review scope
- `checkpoint_proposal_id` identifies one reconciliation-owned checkpoint
  proposal record before acceptance
- `kernel_scope_id` identifies one shared gap/review attachment scope over one
  canonical product kernel and is not a substitute for a narrower scope
- do not attach a gap or review to `kernel_scope` when `subject`,
  `selection`, `claim_scope`, `continuity_segment`,
  `balance_target`, or `checkpoint_proposal` would be truthful

### `kernel_scope_id`

`kernel_scope_id` is defined once for target gap, review, and declared
derived-output attachments.

Rules:

- `kernel_scope_id` is `<product_slug>:<kernel_fingerprint>`
- `scope` is the right noun here because this id names a shared attachment
  boundary over one emitted kernel, not the product identity itself
- `product_slug` uses the lower-snake-case target product stem
- `kernel_fingerprint` is the canonical product fingerprint owned by
  [Pipeline Stage Contracts](pipeline-stage-contracts.md)
- `kernel_scope_id` is derived after canonical kernel fingerprinting and is not
  a product header field or a fingerprint input itself
- `kernel_scope_id` is never a target product id, never an upstream product
  ref, and never the primary reader key when one product id or narrower record
  id exists
- `kernel_scope_id` is used only for gap/review sidecar attachment and
  declared derived outputs when no narrower truthful subject or scope exists
- `kernel_scope_id` must not replace `selection_id`,
  `claim_scope_id`, `continuity_segment_id`, `balance_target_id`,
  `checkpoint_proposal_id`, or one record id when those are truthful

## Shared Stage Vocabulary

Use one stage vocabulary across gap records, review records, checkpoint-stage
reuse, and any later capability-owned derived outputs.

Shared stage vocabulary:

- `evidence`
- `claim`
- `economics`
- `reconciliation`
- `checkpoint`
- `journal`
- `tax`

Rules:

- `owner_stage` and `blocking_stages` use this vocabulary
- later capability-owned derived outputs use this vocabulary
- keep stage labels on repo-owned noun forms that match the target package and
  ownership docs
- do not use alternate labels such as `semantic` once target-stage products
  are emitted

## Gap Model

The target shared gap model splits compact blocking truth from explanation.
`GapRecord` and `ReviewRecord` stay short because each one names the shared
cross-stage business concept directly rather than a local helper wrapper.

### `GapRecord`

Purpose:

- compact shared blocker record used across stages

Kernel fields:

- `gap_id`
- `owner_stage`
- `blocking_stages`
- `scope_kind`
- `scope_ref`
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
  - `kernel_scope`
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
- `scope_key` uses `scope_ref` when `scope_kind` is not `subject`
- `scope_ref` is required when `scope_kind` is not `subject`
- `subject_ref` is required when `scope_kind` is `subject`
- `gap_key` is the stage-owned stable discriminator for one blocking
  condition inside the declared scope

Ordering:

- sort by tuple
  `[owner_stage, scope_kind, subject_ref, scope_ref, gap_kind, gap_id]`
- use JSON `null` ordering for inactive `subject_ref` and `scope_ref` fields

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
- `owner_stage` identifies who owns the gap meaning
- `blocking_stages` identifies who is blocked by the unresolved condition
- stages may add stage-local subtyping later, but they must not redefine the
  gap and review contracts out of existence
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
- `scope_ref`
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
  - `kernel_scope`
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
- `scope_key` uses `scope_ref` when `scope_kind` is not `subject`
- `review_kind` is the owner-stage stable advisory label for one review family
- `review_key` is the owner-stage stable discriminator for one advisory
  observation inside the declared scope

Ordering:

- sort by tuple
  `[owner_stage, scope_kind, subject_ref, scope_ref, review_kind, review_id]`
- use JSON `null` ordering for inactive `subject_ref` and `scope_ref` fields
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

## Readiness Locality

Readiness is not a shared assessment family.

Rules:

- readiness is always a capability-owned derived view over authoritative
  stage-owned records plus open gaps
- readiness views may key off truthful subject ids, stage-local scope ids such
  as `claim_scope_id`, `continuity_segment_id`, `balance_target_id`, and
  `checkpoint_proposal_id`, or declared product-local grouping keys when the
  owning capability defines them
- the tax-first path may keep the frozen `TaxOutputs`-local grouped readiness
  output owned by
  [Pipeline Stage Contracts](pipeline-stage-contracts.md) and
  [Reconciliation, Checkpoint, Journal, And Tax Architecture](reconciliation-tax-architecture.md)
- compatibility-local or rendering-local readiness views may exist where live
  readers need them, but they do not create a shared readiness record family
- broader grouped readiness or durable projections outside tax-local or
  compatibility-local surfaces require the roadmap trigger ladder to activate a
  capability-owned derived read-model slice

## Sidecar Taxonomy

Use one explicit sidecar taxonomy across the target docs.

Shared assessment families:

- `assessment/gap/` for `GapRecord` and `GapExplanation`
- `assessment/review/` for `ReviewRecord` and `ReviewExplanation`

Product-local detail families:

- provenance detail
- comparison traces
- annotations
- policy notes and rendered policy detail
- other product-owned explanatory detail that does not change the owning
  product's kernel meaning

Compatibility families:

- migration-only `compatibility/` views and sidecars for retained bridge
  readers

Derived outputs, caches, and indexes:

- non-authoritative grouped outputs
- caches
- indexes

Rules:

- shared assessment records and explanation families are declared persisted
  outputs; they are not disposable accelerators
- product-local detail families belong under explicit product-local family names
  chosen by the owning product and never under `assessment/`
- compatibility families stay migration-only and must not become a second
  architecture center
- derived outputs, caches, and indexes are the regenerable class; they remain
  reproducible from authoritative kernels plus declared upstream refs

## Bridge Mapping From Issue And Review Records

**Compatibility-only locality:** This section names current bridge records only
to define how those compatibility-local surfaces map into the target gap and
review families. They do not become target-domain family names.

The live bridge still emits `IssueRecord` and `NormalizationReviewRecord`.

Mapping rules:

- a blocking `IssueRecord` maps to one `GapRecord` plus one `GapExplanation`
  when owner stage, blocking stages, scope, and blocker meaning align
- `IssueRecord.kind`, `severity`, `context_timestamp`, and typed provenance are
  gap inputs, not free text to reinterpret later
- `NormalizationReviewRecord` maps to one `ReviewRecord` plus one
  `ReviewExplanation` when owner stage, scope, and advisory meaning align
- when one factual cause produces both a blocker and an advisory review, the
  blocker lands in `GapRecord` and the review remains keyed shared-assessment
  detail
- if an operator or bridge consumer still needs readiness after cutover, define
  it as a capability-owned derived view over target products plus shared gap
  and review outputs rather than as a shared readiness record family
- current bridge ids remain traceable when later stages adopt target-native gap
  or review ids

## Anti-Duplication And Sidecar Rules

Copy only when meaning changes.

Meaning:

- one stage owns one meaning surface
- downstream stages reference upstream records by stable ids or product ids
- `kernel_scope_id` is allowed only for declared derived outputs and sidecar
  attachment when no narrower truthful product id, scope id, or record id
  exists
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

Use shared assessment families only for:

- gaps
- reviews

Use product-local detail families for:

- provenance
- annotations
- comparison traces
- policy explanations

Use derived outputs, caches, and indexes only for:

- grouped readiness and other grouped views
- caches
- indexes

Sidecars must never become:

- the only real copy of business meaning
- a substitute for unresolved business concepts
- a junk drawer of unresolved text

Performance implication:

- avoiding meaning duplication is also a performance rule
- repeated full detail copies increase read amplification, join cost, and drift
  risk
- the correct shape is stable ids or product ids plus stage-owned deltas, with
  `kernel_scope_id` reserved for declared derived outputs or sidecar
  attachment only

## Current-To-Target Boundary

**Compatibility-only locality:** These current bridge family names stay here
only to document the migration boundary. They do not remain canonical target
vocabulary after cutover.

- current `IssueRecord` and `NormalizationReviewRecord` remain live bridge
  outputs today
- later implementation may map current bridge issues and reviews into the
  shared gap/review contracts where stage ownership and meaning line up
- current-state docs keep current issue and review names where accuracy
  requires them
