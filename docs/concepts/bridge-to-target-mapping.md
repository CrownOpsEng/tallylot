---
title: "Bridge To Target Mapping"
summary: "Single authority for how live bridge boundaries map into the target pipeline during Phase 0 and the first bounded increment."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 24
related:
  - docs/concepts/current-bridge-contracts.md
  - docs/concepts/pipeline-stage-contracts.md
  - docs/reference/first-slice-contract.md
  - docs/status/migration-sequence.md
  - ROADMAP.md
---

Use this page when you need the primary mapping from the live bridge into the
target pipeline. This document owns transformation direction and migration
continuity. It does not re-own either live bridge truth or target product
contracts.

## Scope And Naming

Ownership boundaries:

- [Current Bridge Contracts](current-bridge-contracts.md) owns live runtime
  truth for `EconomicActivityDraft`, `SourceTranslationBatch`,
  `TransactionFact`, and the current bridge artifacts.
- [Pipeline Stage Contracts](pipeline-stage-contracts.md) defines the
  meaning of `EvidenceSet`, `ClaimSet`, `EconomicFacts`,
  `ReconciliationState`, `Checkpoint`, `Journal`, `TaxInputs`, and
  `TaxOutputs`.
- this page owns how current bridge boundaries map to bounded proto-products during
  migration, what stays bridge-only, and where continuity rules apply

Naming rules:

- `proto-EvidenceSet` and `proto-ClaimSet` mean bounded coverage of the
  target products during migration
- `proto-` is a coverage label, not a competing noun or alternate architecture
- `SourceTranslationBatch` remains the live migration boundary until a later increment
  replaces it; do not rename it in current-state docs just to match target
  vocabulary
- the default first increment is the bounded Coinbase-first increment defined in
  [First Slice Contract](../reference/first-slice-contract.md)
- the repo does not infer the actual `2023` to `2025` filing adapter inventory
  from these docs; that inventory remains an external delivery-note input until
  a concrete workspace source list is recorded separately

## Live Bridge Inventory

The current bridge families that matter for target mapping are:

| Current output | Current owner | Current role |
| --- | --- | --- |
| `translation_input_candidates.json` | planner-enabled normalization | deterministic candidate inventory before translation |
| `translation_input_plan.json` | planner-enabled normalization | selected, superseded, and blocked candidate decisions |
| `translation_input_issues.csv` | planner-enabled normalization | candidate-selection blocking diagnostics |
| statement parse outputs and statement-backed quantity rows | shared statement extraction | boundary-parsed quantity observations and source-backed support |
| `EconomicActivityDraft` | translation boundary | provider-local semantic draft before shared fact acceptance |
| `SourceTranslationBatch` | translation boundary | migration bundle of drafts, balance references, issues, reviews, and inventory |
| `TransactionFact` and `facts.csv` | current bridge | accepted bridge approximation of economic truth |
| `balance_snapshots.csv` | current bridge | derived balance cutoff snapshots over current facts |
| `balance_references.csv` | current bridge | quantity-backed support references for balances |
| `exceptions.csv` and `normalization_reviews.csv` | current bridge | stage-local issue and review artifacts |
| `fact_annotations.json` and `location_annotations.json` | current bridge sidecars | bridge-only sidecars keyed to emitted bridge outputs |

## Bridge-To-Target Mapping Table

| Current output | Target destination | Mapping rule | Bridge status during migration |
| --- | --- | --- | --- |
| `translation_input_candidates.json` | `EvidenceSet` envelope and selection sidecars | preserve planner candidate membership, coverage, and comparability as evidence-selection reasoning; these candidates do not become `EvidenceSet` kernel records | remains bridge-owned until `EvidenceSet` lands |
| `translation_input_plan.json` | `EvidenceSet` kernel | selected, superseded, and blocked planner decisions from this file supply the kernel `selection_status` records under one deterministic `selection_group_id` | dual-emitted during the first increment |
| recognized statement balance rows | `EvidenceSet` observations and `BalanceObservationClaim` inputs | preserve statement document identity, row identity, as-of time, precision, quantity, and provenance as typed observations under the owning statement document without forcing final checkpoint acceptance | dual-emitted during the first increment |
| `EconomicActivityDraft` | `ClaimSet` | split one draft into `ActivityClaim`, `InstrumentIdentityClaim`, `LocationClaim`, `BalanceObservationClaim`, `ValuationClaim`, `ProjectionAnnotation`, issue candidates, and review candidates | bridge boundary remains live until claim-native increments replace it |
| `SourceTranslationBatch` | migration continuity between `EvidenceSet`, `ClaimSet`, and current bridge outputs | keep the bundled bridge boundary honest while bounded proto-products are emitted beside it | live runtime boundary |
| `TransactionFact` | bridge-only approximation of `EconomicFacts` | treat accepted bridge facts as the current approximation of accepted economic meaning, not as the final target contract | bridge-only until `EconomicFacts` lands |
| `balance_snapshots.csv` | later `ReconciliationState` inputs | keep derived snapshots bridge-only; do not claim that they are target reconciliation kernels | bridge-only |
| `balance_references.csv` | later `Checkpoint` and `ReconciliationState` inputs | keep source-backed and operator assertion references explicit as checkpoint or reconciliation inputs, not accepted checkpoint truth by themselves | bridge-only |
| `IssueRecord` outputs | `GapCore` plus `GapExplanation` where semantics align | blocking current issues map to target gaps only when owner stage, scope, and blocker meaning are preserved | bridge-only until a stage adopts target gaps |
| `NormalizationReviewRecord` outputs | review sidecars and paired gap explanations | advisory reviews remain review sidecars unless a paired blocking gap exists | bridge-only until a stage adopts target reviews |

## Bridge-Only Outputs That Remain

The following outputs remain bridge-only even after the first increment starts
emitting bounded proto-products:

- `SourceTranslationBatch` remains the live transition bundle until later
  increments replace it end to end
- `TransactionFact` remains the accepted bridge approximation of economic truth
  and must not be described as the final `EconomicFacts` kernel
- bridge-era balance artifacts remain runtime inputs and reporting outputs, not
  target reconciliation or checkpoint products
- `accounting_intent_hint`, `tax_treatment_hint`, and `projection_hint` remain
  bridge-era hint lanes that later stages may reference but must not recenter
  as target economic truth
- fact and location annotations remain bridge sidecars; they do not become the
  only copy of claim, economic, reconciliation, or checkpoint meaning

## Issue And Review Migration

Mapping rules from live bridge diagnostics into the target support model:

- a blocking `IssueRecord` becomes one `GapCore` plus one `GapExplanation`
  only when the target stage can preserve the same owner stage, blocking
  stages, scope, materiality, and confidence
- `issue_id` remains the stable bridge diagnostic id until the replacement
  stage emits its own target-native ids; do not invent a new id family without
  carrying a stable source reference
- `kind`, `severity`, `context_timestamp`, and typed provenance become gap
  inputs, not free text to be reinterpreted later
- an advisory `NormalizationReviewRecord` remains a review sidecar unless a
  paired blocking condition also exists
- when one blocking condition and one review share the same factual cause, the
  gap owns the blocker and the review remains a sidecar keyed to the same
  subject, scope, or decision record
- do not upgrade reviews into gaps or downgrade gaps into reviews just to keep
  bridge facts flowing

The target support contracts still live in
[Gaps And Readiness](gaps-and-readiness.md). This page only fixes the current
bridge-to-target mapping rule.

## First-Increment Mapping Rules

The default first increment is intentionally narrow:

- planner-enabled Coinbase retail export evidence
- recognized Coinbase statement-backed balance observation flow
- continued compatibility with current `SourceTranslationBatch`,
  `TransactionFact`, `balance_references.csv`, and `cointracking_csv`

First-increment rules:

- `translation_input_candidates.json` remains planner candidate reasoning in
  the `EvidenceSet` envelope or selection sidecars, while
  `translation_input_plan.json` supplies the kernel `selection_status` records
  for the increment
- recognized statement rows become evidence observations first and
  `BalanceObservationClaim` inputs second; they do not become evidence member
  families or accepted checkpoint truth inside the increment
- `EconomicActivityDraft` remains the provider-local pre-economic bridge boundary,
  but its responsibilities are split conceptually into claim families so later
  increments do not need to rediscover that cut
- the shared compiler remains responsible for producing current bridge outputs
  from accepted claims until `EconomicFacts` and later downstream products
  replace that responsibility
- first-slice observation classes, evidence member families, and bounded
  `selection_group_id` rules are frozen only on
  [First Slice Contract](../reference/first-slice-contract.md)
- the first increment must not create a second active runtime center, a permanent
  dual-write lane, or a repo-wide adapter-facet migration prerequisite
- unchanged evidence must preserve selected evidence membership, claim identity
  and ordering, compiled bridge facts, balance reference kinds, and
  `cointracking_csv` projection compatibility as defined in
  [First Slice Contract](../reference/first-slice-contract.md)
