---
title: "Bridge To Target Mapping"
summary: "Single authority for how live bridge surfaces cut over to target products during migration, including writer ownership, reader cutovers, and retirement gates."
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
target pipeline. This document owns transformation direction, authoritative
writer rules, derived compatibility projections, reader cutovers, and bridge
retirement gates. It does not re-own live bridge truth or target product
contracts.

## Scope And Owner Pages

Ownership boundaries:

- [Current Bridge Contracts](current-bridge-contracts.md) owns live runtime
  truth for `EconomicActivityDraft`, `SourceTranslationBatch`,
  `TransactionFact`, and the current bridge surfaces.
- [Pipeline Stage Contracts](pipeline-stage-contracts.md) owns the target
  product kernels, ids, ordering, serialization, and fingerprints for
  `EvidenceSet`, `ClaimSet`, `EconomicFacts`, `ReconciliationState`,
  `Checkpoint`, `Journal`, `TaxInputs`, and `TaxOutputs`.
- [Gaps And Readiness](gaps-and-readiness.md) owns `GapRecord`,
  `GapExplanation`, `ReviewRecord`, `ReviewExplanation`,
  `ReadinessRecord`, `ReadinessRollupRecord`, and `SubjectRef`.
- this page owns how bridge surfaces move to target products without creating
  dual authorities

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
  projection only

Consumer rule:

- a consumer may read the bridge surface or the target product, never both as
  peer authorities
- if a consumer is not yet migrated, it reads the derived bridge projection
- if a consumer is migrated, it reads the target product only

Compatibility rule:

- unchanged bridge outputs during the compatibility window must be reproducible
  from the authoritative target kernel plus its declared upstream refs
- compatibility projections may add bridge-local formatting or schema shaping,
  but they may not invent meaning that is absent from the authoritative target
  product

No-dual-center rule:

- `SourceTranslationBatch`, `TransactionFact`, `balance_snapshots.csv`, and
  `balance_references.csv` may remain live compatibility surfaces during
  migration
- none of those surfaces may remain a second architecture center once the
  corresponding target product is authoritative for that scope

## Cutover Matrix

Every implementation slice must name the authoritative writer and active reader
for each affected surface before code lands. Use this matrix as the default
cutover contract.

| Current surface | Authoritative surface now | Authoritative surface after slice | Derived compatibility projection | Active readers now | Target readers after cutover | Cutover gate | Retirement gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `translation_input_candidates.json` | planner-enabled normalization | `EvidenceSet` kernel plus planning sidecar | optional planner review projection derived from `EvidenceSet` plus planning sidecar | normalization review tools and planner inspection flows | evidence review and claim-construction flows that read `EvidenceSet` directly | selected, superseded, and blocked membership are preserved with stable `selection_id` and `member_id` outcomes | retire once planner/operator review surfaces no longer require the legacy file |
| `translation_input_plan.json` | planner-enabled normalization | `EvidenceSet` | `translation_input_plan.json` regenerated from `EvidenceSet` during the compatibility window | translation entry points that still expect a plan file | evidence consumers and claim construction that read `EvidenceSet` directly | one authoritative `EvidenceSet` exists for the capture and reproduces the same selected, superseded, and blocked decisions | retire when no in-scope reader requires the plan file and parity is enforced on `EvidenceSet` instead |
| recognized statement parse outputs and balance rows | shared statement extraction outputs | `EvidenceSet` observations | statement-facing compatibility sidecar derived from `EvidenceObservationRecord` sidecars | normalization review and statement debugging flows | claim construction and downstream support flows that read `EvidenceSet` observations | statement-document detail, row keys, quantities, and provenance are preserved under `EvidenceSet` | retire legacy parse-only outputs when all readers use `EvidenceSet` observations or declared sidecars |
| `EconomicActivityDraft` | source translation boundary | `ClaimSet` | `EconomicActivityDraft` rows derived from accepted `ClaimBundleRecord` and `ClaimRecord` kernels plus declared compatibility sidecars keyed by `claim_id` or `claim_bundle_id` for `economic_kind`, `projection_hint`, `accounting_intent_hint`, `tax_treatment_hint`, `description`, `tx_hash_or_null`, `operation_group_id_or_null`, `confidence`, and `status` | `SourceTranslationBatch` assembly and bridge compilers | economic-fact construction that reads `ClaimSet` directly | claim field tables, `observation_refs`, claim-bundle selection, and the retained legacy claim fields are all frozen for the first upstream slice in either `ClaimSet` kernels or declared compatibility sidecars | retire when no bridge compiler or batch builder still consumes drafts |
| `SourceTranslationBatch` | source translation boundary | `ClaimSet` | `SourceTranslationBatch` projection derived from `ClaimSet` plus declared compatibility sidecars for `economic_kind`, `projection_hint`, `accounting_intent_hint`, `tax_treatment_hint`, `description`, `tx_hash_or_null`, `operation_group_id_or_null`, `confidence`, and `status`, plus shared support records and sidecars | current normalization application surface and bridge interop flows | target application paths in `application/claim/` and later `application/economics/` | in-scope readers can be pointed to `ClaimSet` or a declared compatibility surface without meaning loss, and no retained batch-only field remains undefined | retire when no active runtime path reads the batch as its primary claim surface |
| `TransactionFact` and `facts.csv` | current bridge fact path | `EconomicFacts` | `TransactionFact` rows and `facts.csv` rendered from `EconomicFacts` plus declared upstream claim compatibility sidecars for `economic_kind`, `projection_hint`, `accounting_intent_hint`, `tax_treatment_hint`, `description`, `tx_hash_or_null`, `operation_group_id_or_null`, `confidence`, and `status` when legacy hint reproduction still needs them | balance builders, output renderers, oracle comparison flows | reconciliation, checkpoint, journal, and tax paths that read `EconomicFacts` | accepted `EconomicEventRecord` and `EconomicLegRecord` parity is proven and current bridge facts are reproducible from `EconomicFacts` plus declared upstream compatibility sidecars rather than from bridge surfaces as peer authorities | retire when no runtime reader depends on `TransactionFact` as economic authority |
| `balance_snapshots.csv` | current bridge balance reducers | `ReconciliationState` | `balance_snapshots.csv` derived from `ReconciliationState` for unmigrated balance surfaces | balance inspect/check/summarize and downstream review workflows | reconciliation readers and later checkpoint assembly that read `ReconciliationState` | continuity segments and balance targets exist for the in-scope subjects and reproduce current snapshot results | retire when active balance surfaces read `ReconciliationState` directly |
| `balance_references.csv` | current bridge balance support path | `Checkpoint` and `ReconciliationState` | `balance_references.csv` derived from `ReconciliationState`, `Checkpoint`, and declared support sidecars | balance inspect/check/summarize and current checkpoint support workflows | checkpoint assembly and reconciliation readers that consume target support directly | direct `AssertionValue` fields, checkpoint proposal records, and `CheckpointAssertionRecord` rows reproduce the current reference content for in-scope subjects | retire when no active surface consumes the CSV as its authoritative support input |
| `exceptions.csv` and bridge `IssueRecord` outputs | stage-local bridge diagnostics | target product plus shared support records | issue compatibility projection derived from `GapRecord` and `GapExplanation` when a target stage owns the blocker | operator review and current normalization diagnostics | target support reducers and readiness views | the owning target stage can preserve blocker scope, severity, materiality, and stage ownership | retire per stage when that stage emits target-native gaps for the same scope |
| `normalization_reviews.csv` and `NormalizationReviewRecord` outputs | stage-local bridge advisory diagnostics | target product plus shared support records and sidecars | review compatibility projection derived from `ReviewRecord` and `ReviewExplanation` | operator review and current normalization diagnostics | target review and readiness views | advisory review scope and provenance are preserved without turning reviews into blockers | retire per stage when that stage emits target-native reviews for the same scope |
| `fact_annotations.json` and `location_annotations.json` | bridge-only sidecar generation | target products plus bridge/output compatibility sidecars | derived annotation sidecars keyed to target ids or bridge projection ids | current bridge renderers and comparison tooling | target-aware output and comparison flows that no longer require annotation sidecar detail embedded in claim surfaces | no target meaning depends on annotation sidecar detail and bridge/output consumers can read derived sidecars instead | retire when the affected renderer or comparison flow no longer depends on the annotation file |

## Compatibility Sidecars And Support Mapping

Bridge-only annotations and diagnostics keep their meaning only as compatibility
surfaces during migration.

Rules:

- bridge or output annotation sidecars remain compatibility detail only
- no target `ClaimSet` kind may be introduced for bridge hints, render notes,
  or output annotations
- if a current renderer or comparison path still needs annotation content, emit
  it as a derived compatibility sidecar keyed to the relevant `claim_id`, `event_id`, or
  bridge projection id
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
- support records and sidecars never become claim kinds

## Current First Slice Rules

The first upstream slice and first downstream slice use this page as their
migration authority.

Required cutovers now:

- `translation_input_plan.json` becomes a compatibility projection from
  `EvidenceSet`
- `EconomicActivityDraft` and `SourceTranslationBatch` become compatibility
  projections from `ClaimSet`
- `TransactionFact` becomes a compatibility projection from `EconomicFacts`
- `balance_snapshots.csv` becomes a compatibility projection from
  `ReconciliationState`
- `balance_references.csv` becomes a compatibility projection from
  `ReconciliationState` and `Checkpoint`
- current balance inspect/check/summarize remains on bridge compatibility
  projections until those application surfaces are repointed to target products

## Retirement Discipline

No bridge surface is retired until all of the following are true:

- the authoritative target product for the affected scope is persisted
- every active reader for that scope has a declared target reader or derived
  compatibility reader
- parity and replay gates for the affected slice pass on unchanged evidence
- current-state docs are updated if the live runtime surface actually changed

Bridge retirement is therefore per scope and per reader, not one repo-wide
rename event.
