---
title: "Bridge To Target Mapping"
summary: "Migration cutover rules for moving live bridge surfaces to target products, compatibility views, and retirement gates."
doc_type: concept
audience: human
owner: repo
status: active
naming_scope: forward_target
nav_order: 24
related:
  - docs/concepts/current-bridge-contracts.md
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/gaps-and-reviews.md
  - docs/reference/evidence-claim-contract.md
  - docs/reference/economics-reconciliation-checkpoint-contract.md
  - docs/status/migration-sequence.md
  - ROADMAP.md
---

Use this page when you need the migration rule from the live bridge into the
target pipeline. This page defines cutover direction, authoritative writer
rules, derived compatibility views, reader cutovers, and bridge retirement
gates. It does not redefine live bridge truth or target product contracts.

**Locality rule:** This migration page restates bridge-only fields such as
`activity_label`, `provider_operation_key`, and the current `*_hint` families
only to freeze compatibility boundaries. Those names stay outside canonical
target kernels.

## Scope And Related Contract Pages

Use these pages for neighboring contracts:

- [Current Bridge Contracts](current-bridge-contracts.md) defines live runtime
  truth for `EconomicActivityDraft`, `SourceTranslationBatch`,
  `TransactionFact`, and the current bridge surfaces.
- [Pipeline Stage Contracts](pipeline-stage-contracts.md) defines the target
  product kernels, ids, ordering, serialization, and fingerprints for
  `EvidenceSet`, `ClaimSet`, `EconomicFacts`, `ReconciliationState`,
  `Checkpoint`, `Journal`, `TaxInputs`, and `TaxOutputs`.
- [Gap, Review, And Shared Attachment](gaps-and-reviews.md) defines
  `GapRecord`, `GapExplanation`, `ReviewRecord`, `ReviewExplanation`,
  `SubjectRef`, and `kernel_scope_id`.
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

**Compatibility-only locality:** The retained bridge view and file names in the
rules below stay compatibility-local during migration.

No-dual-center rule:

- `SourceTranslationBatch`, `TransactionFact`, `balance_snapshots.csv`, and
  `balance_references.csv` may remain live compatibility views during
  migration
- none of those surfaces may remain a second architecture center once the
  corresponding target product is authoritative for that scope
- broader grouped consumers stay on authoritative kernels, compatibility views, or tax-output-local and rendering-local derived outputs while broader derived read models and projections stay deferred, and they move only when a later capability-specific increment requires a dedicated derived read-model slice
- the bounded economics/reconciliation/checkpoint contract is now implemented
  for planner-enabled Coinbase normalization, so `TransactionFact`,
  `facts.csv`, `balance_snapshots.csv`, and `balance_references.csv` are
  target-derived compatibility views for the current readers that still depend
  on those bridge-local surfaces
- the evidence/claim contract still does not authorize a second independent
  fact-reducer lane from `ClaimSet`; downstream parity now flows through the
  authoritative `EconomicFacts`, `ReconciliationState`, and `Checkpoint`
  kernels instead

## Cutover Matrix

Every implementation slice must name the authoritative writer and active reader
for each affected surface before code lands. Use this matrix as the default
cutover contract.

**Compatibility-only locality:** The matrix below names current bridge files,
views, and records only to define migration cutovers. Those surfaces remain
compatibility-local and do not become canonical target-domain family names.

| Current bridge surface | Target authoritative product(s) | Derived compatibility view | Derived compatibility sidecar | Current readers | Target readers after cutover | Cutover gate | Retirement gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `translation_input_candidates.json` | `EvidenceSet` | `none` | `none` | `source normalize planner review and translation path` | evidence review and selection inspection from `EvidenceSet` | selected, superseded, and blocked membership are preserved with stable `selection_id` and `member_id` outcomes | retire once no active evidence review or selection inspection requires the file |
| `translation_input_plan.json` | `EvidenceSet` | `translation_input_plan.json` | `none` | `source normalize planner review and translation path` | claim construction from `EvidenceSet` | one authoritative `EvidenceSet` exists for the capture and reproduces the same selected, superseded, and blocked decisions | retire when no in-scope reader requires the plan file and parity is enforced on `EvidenceSet` instead |
| `EconomicActivityDraft` | `ClaimSet` | `EconomicActivityDraft` | `compatibility sidecar` | `source assemble bridge projection path` | economics construction from `ClaimSet` | claim field tables, `observation_refs`, claim-bundle decisions, and retained legacy claim fields are all frozen in `ClaimSet` kernels or declared compatibility sidecars | retire when no active bridge projection path still consumes drafts |
| `SourceTranslationBatch` | `ClaimSet` | `SourceTranslationBatch` | `compatibility sidecar` | `source assemble bridge projection path` | economics construction from `ClaimSet` | in-scope readers can be pointed to `ClaimSet` or a declared compatibility view without meaning loss, and no retained batch-only field remains undefined | retire when no active bridge projection path reads the batch as its primary claim surface |
| `TransactionFact` and `facts.csv` | `EconomicFacts` | `TransactionFact` and `facts.csv` | `compatibility sidecar` | `reconciliation balances check`; `cointracking_csv rendering path`; `dev-only oracle comparison path` | `reconciliation balances check` reading compatibility output derived from `EconomicFacts`; `cointracking_csv rendering path` reading compatibility output derived from `EconomicFacts`; `dev-only oracle comparison path` reading compatibility output derived from `EconomicFacts` | accepted `EconomicEventRecord` and `EconomicLegRecord` parity is proven and current bridge facts are reproducible from `EconomicFacts` plus declared upstream compatibility sidecars | retire when no active runtime capability depends on `TransactionFact` as economic authority |
| `balance_snapshots.csv` | `ReconciliationState` | `balance_snapshots.csv` | `none` | `reconciliation balances inspect`; `reconciliation balances check`; `reconciliation balances summarize` | `reconciliation balances inspect` reading `ReconciliationState`; `reconciliation balances check` reading `ReconciliationState`; `reconciliation balances summarize` reading `ReconciliationState` | continuity segments and balance targets exist for the in-scope subjects and reproduce current snapshot results | retire when the active balance capabilities read `ReconciliationState` directly |
| `balance_references.csv` | `ReconciliationState` and `Checkpoint` | `balance_references.csv` | `compatibility sidecar` | `reconciliation balances inspect`; `reconciliation balances check`; `reconciliation balances summarize` | checkpoint acceptance reading `ReconciliationState` plus `Checkpoint`; `reconciliation balances inspect` reading compatibility output derived from `ReconciliationState` plus `Checkpoint`; `reconciliation balances check` reading compatibility output derived from `ReconciliationState` plus `Checkpoint`; `reconciliation balances summarize` reading compatibility output derived from `ReconciliationState` plus `Checkpoint` | direct `AssertionValue` fields, checkpoint proposal records, and `CheckpointAssertionRecord` rows reproduce the current reference content for in-scope subjects | retire when no active surface consumes the CSV as its authoritative reference input |
| `exceptions.csv` and `IssueRecord` outputs | owning target product plus `GapRecord` and `GapExplanation` | `exceptions.csv` | `none` | `operator review diagnostics` | `operator review diagnostics` reading the owning target product plus target-native gap outputs and capability-owned readiness views when needed | the owning target stage preserves blocker scope, severity, materiality, and stage ownership | retire per stage when that stage emits target-native gaps for the same scope |
| `normalization_reviews.csv` and `NormalizationReviewRecord` outputs | owning target product plus `ReviewRecord` and `ReviewExplanation` | `normalization_reviews.csv` | `none` | `operator review diagnostics` | `operator review diagnostics` reading the owning target product plus target-native review outputs and capability-owned readiness views when needed | advisory review scope and provenance are preserved without turning reviews into blockers | retire per stage when that stage emits target-native reviews for the same scope |

Shared assessment outputs named in the target-authority column stay separate
from compatibility sidecars. They are not compatibility surfaces in disguise.

Reader-label glossary:

- `source normalize planner review and translation path` is the planner-enabled
  normalization review and translation flow defined in
  [Current State](../status/current-state.md)
- `source assemble bridge projection path` is the `source assemble` bridge
  projection flow that still consumes `EconomicActivityDraft` and
  `SourceTranslationBatch`
- `operator review diagnostics` is operator review of `exceptions.csv`,
  `normalization_reviews.csv`, and related current diagnostics
- `reconciliation balances inspect`, `reconciliation balances check`, and
  `reconciliation balances summarize` are the shared balance capabilities in the
  current application surface
- `cointracking_csv rendering path` is the current CSV rendering path
- `dev-only oracle comparison path` is the dev-only oracle comparison and
  validation path

These reader labels are authoritative across the migration docs.

Planner review traces and statement-parse debugging outputs remain real local
workflow artifacts, but they do not appear as canonical matrix rows until the
repo declares them as stable file, view, or sidecar families.

If current renderers or comparison flows still need annotation material such as
`fact_annotations.json` or `location_annotations.json`, keep that detail in
derived compatibility sidecars keyed to target ids or bridge-view ids. Those
files remain compatibility-local and do not appear as canonical target matrix
families.

## Compatibility Sidecars And Gap/Review Mapping

**Compatibility-only locality:** This section names bridge records and files
only to preserve truthful migration mappings for active compatibility
surfaces.

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
- shared gap and review outputs never become claim kinds
- any readiness that operators or renderers still need after cutover must stay
  on capability-owned derived views rather than on shared assessment families

## Current First Slice Rules

**Compatibility-only locality:** These retained filenames stay here only to
document the active compatibility window for the first bounded slices.

The bounded evidence/claim and economics/reconciliation/checkpoint contracts use this page as their
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
- the evidence/claim contract must not introduce a second downstream fact lane
  before the economics/reconciliation/checkpoint contract lands
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
