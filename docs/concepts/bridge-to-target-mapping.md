---
title: "Bridge To Target Mapping"
summary: "Migration cutover rules for moving live bridge surfaces to target products, compatibility views, and retirement gates."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 24
related:
  - docs/concepts/current-bridge-contracts.md
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/gaps-and-readiness.md
  - docs/reference/first-upstream-slice-contract.md
  - docs/reference/first-downstream-slice-contract.md
  - docs/status/migration-sequence.md
  - ROADMAP.md
---

Use this page when you need the migration rule from the live bridge into the
target pipeline. This page defines cutover direction, authoritative writer
rules, derived compatibility views, reader cutovers, and bridge retirement
gates. It does not redefine live bridge truth or target product contracts.

## Scope And Related Contract Pages

Use these pages for neighboring contracts:

- [Current Bridge Contracts](current-bridge-contracts.md) defines live runtime
  truth for `EconomicActivityDraft`, `SourceTranslationBatch`,
  `TransactionFact`, and the current bridge surfaces.
- [Pipeline Stage Contracts](pipeline-stage-contracts.md) defines the target
  product kernels, ids, ordering, serialization, and fingerprints for
  `EvidenceSet`, `ClaimSet`, `EconomicFacts`, `ReconciliationState`,
  `Checkpoint`, `Journal`, `TaxInputs`, and `TaxOutputs`.
- [Gaps And Readiness](gaps-and-readiness.md) defines `GapRecord`,
  `GapExplanation`, `ReviewRecord`, `ReviewExplanation`,
  `ReadinessRecord`, `ReadinessRollupRecord`, and `SubjectRef`.
- this page defines how bridge surfaces move to target products without
  creating dual authorities

Naming rules:

- current-state docs keep bridge names where they describe implemented runtime
  truth
- forward-looking docs use target product names directly, even when a slice has
  bounded coverage
- bridge or output annotation sidecar detail is not `ClaimSet` kernel meaning; if
  compatibility still needs annotation material, it must live in a derived
  compatibility sidecar

## Migration Authority Rules

Authoritative writer rule:

- as soon as a target product exists for an in-scope family, that product
  becomes the sole authoritative persisted truth surface for that scope
- any remaining bridge surface for that scope becomes a derived compatibility
  view only

Consumer rule:

- a consumer may read the bridge surface or the target product, never both as
  peer authorities
- if a consumer is not yet migrated, it reads the derived bridge view
- if a consumer is migrated, it reads the target product only

Compatibility rule:

- unchanged bridge outputs during the compatibility window must be reproducible
  from the authoritative target kernel plus its declared upstream refs
- compatibility views may add bridge-local formatting or schema shaping,
  but they may not invent meaning that is absent from the authoritative target
  product

No-dual-center rule:

- `SourceTranslationBatch`, `TransactionFact`, `balance_snapshots.csv`, and
  `balance_references.csv` may remain live compatibility views during
  migration
- none of those surfaces may remain a second architecture center once the
  corresponding target product is authoritative for that scope

## Cutover Matrix

Every implementation slice must name the authoritative writer and active reader
for each affected surface before code lands. Use this matrix as the default
cutover contract.

| Current bridge surface | Target authoritative product | Derived compatibility view | Derived compatibility sidecar | Current readers | Target readers after cutover | Cutover gate | Retirement gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `translation_input_candidates.json` | `EvidenceSet` | `none` | `none` | normalization review tools and planner inspection flows | evidence review flows that read `EvidenceSet` directly | selected, superseded, and blocked membership are preserved with stable `selection_id` and `member_id` outcomes | retire once no active review flow requires the file |
| `translation_input_plan.json` | `EvidenceSet` | `translation_input_plan.json` | `none` | translation entry points that still expect a plan file | evidence consumers and `ClaimSet` construction that read `EvidenceSet` directly | one authoritative `EvidenceSet` exists for the capture and reproduces the same selected, superseded, and blocked decisions | retire when no in-scope reader requires the plan file and parity is enforced on `EvidenceSet` instead |
| `EconomicActivityDraft` | `ClaimSet` | `EconomicActivityDraft` | declared claim compatibility sidecars keyed by `claim_id` or `claim_bundle_id` | `SourceTranslationBatch` assembly and bridge fact projection builders | `EconomicFacts` construction that reads `ClaimSet` directly | claim field tables, `observation_refs`, claim-bundle decisions, and retained legacy claim fields are all frozen in `ClaimSet` kernels or declared compatibility sidecars | retire when no bridge fact projection builder or batch builder still consumes drafts |
| `SourceTranslationBatch` | `ClaimSet` | `SourceTranslationBatch` | declared claim compatibility sidecars plus shared gap/review/readiness sidecars | current normalization application surface and bridge interop flows | target application paths in `application/claim/` and later `application/economics/` | in-scope readers can be pointed to `ClaimSet` or a declared compatibility view without meaning loss, and no retained batch-only field remains undefined | retire when no active runtime path reads the batch as its primary claim surface |
| `TransactionFact` and `facts.csv` | `EconomicFacts` | `TransactionFact` and `facts.csv` | declared upstream claim compatibility sidecars when legacy hint reproduction still needs them | balance builders, output renderers, oracle comparison flows | reconciliation, checkpoint, journal, and tax paths that read `EconomicFacts` | accepted `EconomicEventRecord` and `EconomicLegRecord` parity is proven and current bridge facts are reproducible from `EconomicFacts` plus declared upstream compatibility sidecars | retire when no runtime reader depends on `TransactionFact` as economic authority |
| `balance_snapshots.csv` | `ReconciliationState` | `balance_snapshots.csv` | `none` | balance inspect/check/summarize and downstream review workflows | reconciliation readers and later checkpoint-acceptance flows that read `ReconciliationState` | continuity segments and balance targets exist for the in-scope subjects and reproduce current snapshot results | retire when active balance surfaces read `ReconciliationState` directly |
| `balance_references.csv` | `Checkpoint` and `ReconciliationState` | `balance_references.csv` | declared reconciliation/checkpoint compatibility sidecars | balance inspect/check/summarize and current checkpoint-reference workflows | checkpoint-acceptance flows and reconciliation readers that consume authoritative reconciliation and checkpoint records plus declared sidecars directly | direct `AssertionValue` fields, checkpoint proposal records, and `CheckpointAssertionRecord` rows reproduce the current reference content for in-scope subjects | retire when no active surface consumes the CSV as its authoritative reference input |
| `exceptions.csv` and `IssueRecord` outputs | target product plus shared gap/review/readiness records | issue compatibility view | `GapExplanation` | operator review and current normalization diagnostics | gap/review/readiness reducers and readiness views | the owning target stage preserves blocker scope, severity, materiality, and stage ownership | retire per stage when that stage emits target-native gaps for the same scope |
| `normalization_reviews.csv` and `NormalizationReviewRecord` outputs | target product plus shared gap/review/readiness records | review compatibility view | `ReviewExplanation` | operator review and current normalization diagnostics | target review and readiness views | advisory review scope and provenance are preserved without turning reviews into blockers | retire per stage when that stage emits target-native reviews for the same scope |
| `fact_annotations.json` and `location_annotations.json` | target products | `none` | derived annotation sidecars keyed to target ids or bridge view ids | current bridge renderers and comparison tooling | target-aware output and comparison flows that no longer require annotation sidecar detail embedded in claim surfaces | no target meaning depends on annotation sidecar detail and bridge/output consumers can read derived sidecars instead | retire when the affected renderer or comparison flow no longer depends on the annotation file |

Planner review traces and statement-parse debugging outputs remain real local
workflow artifacts, but they do not appear as canonical matrix rows until the
repo declares them as stable file, view, or sidecar families.

## Compatibility Sidecars And Gap/Review Mapping

Bridge-only annotations and diagnostics keep their meaning only as compatibility
surfaces during migration.

Rules:

- bridge or output annotation sidecars remain compatibility detail only
- no target `ClaimSet` kind may be introduced for bridge hints, render notes,
  or output annotations
- if a current renderer or comparison path still needs annotation content, emit
  it as a derived compatibility sidecar keyed to the relevant `claim_id`, `event_id`, or
  bridge view id
- legacy claim-local bridge fields such as `economic_kind`, `projection_hint`,
  `accounting_intent_hint`, `tax_treatment_hint`, `description`,
  `tx_hash_or_null`, `operation_group_id_or_null`, `confidence`, and `status`
  remain outside `ClaimSet` kernels and survive only through
  declared compatibility sidecars when a live bridge reader still needs them
- legacy `provider_operation_key` stays satisfied by `activity_label` on
  claims with `kind = activity` and does not require a duplicate
  compatibility-only field

Diagnostic mapping rules:

- a blocking bridge `IssueRecord` maps to `GapRecord` plus `GapExplanation` only
  when the target stage can preserve blocker scope, severity, blocking stages,
  and provenance
- a bridge `NormalizationReviewRecord` maps to `ReviewRecord` plus
  `ReviewExplanation`
- reviews remain advisory even when they share the same factual cause as a gap
- gap, review, and readiness records and sidecars never become claim kinds

## Current First Slice Rules

The first upstream slice and first downstream slice use this page as their
migration authority.

Required cutovers now:

- `translation_input_plan.json` becomes a compatibility view from
  `EvidenceSet`
- `EconomicActivityDraft` and `SourceTranslationBatch` become compatibility
  views from `ClaimSet`
- `TransactionFact` becomes a compatibility view from `EconomicFacts`
- `balance_snapshots.csv` becomes a compatibility view from
  `ReconciliationState`
- `balance_references.csv` becomes a compatibility view from
  `ReconciliationState` and `Checkpoint`
- current balance inspect/check/summarize remains on bridge compatibility
  views until those application surfaces are repointed to target products

## Retirement Discipline

No bridge surface is retired until all of the following are true:

- the authoritative target product for the affected scope is persisted
- every active reader for that scope has a declared target reader or derived
  compatibility reader
- parity and replay gates for the affected slice pass on unchanged evidence
- current-state docs are updated if the live runtime surface actually changed

Bridge retirement is therefore per scope and per reader, not one repo-wide
rename event.
