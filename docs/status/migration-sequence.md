---
title: "Migration Sequence"
summary: "Incremental landing and retirement rules for moving from the current bridge to the target pipeline without dual authorities."
doc_type: status
audience: human
owner: repo
status: active
naming_scope: forward_target
nav_order: 20
---

Use this page to sequence implementation increments without a big-bang refactor.
This page keeps migration rules, cutover expectations, and retirement gates in
one place. It is the durable owner for sequencing, cutover, and bridge
retirement rules. It does not redefine target product contracts or recreate
planning-document delivery detail.

## Planning Document Ownership

[ROADMAP.md](../../ROADMAP.md) is the only numbered implementation program of
record. It remains planning-only and is not the durable contract or
docs-audit authority for sequencing semantics.

Use this page for:

- migration landing rules
- reader and writer cutover expectations
- bridge retirement rules
- parity and replay gates that must hold before one surface is retired

Do not use this page for:

- competing numbered planning labels
- alternate planning labels
- duplicate product-contract definitions
- duplicate ontology, gap/review/shared-attachment, or persistence contracts

## Operating Rules

Every slice must obey the following rules before code lands:

- declare the slice scope
- name the authoritative writer for every affected scope
- name the authoritative reader for every affected consumer using concrete
  current runtime capabilities rather than generic category labels
- declare the product id and upstream product-ref fields carried in each target
  product header the slice introduces
- name the derived compatibility view for every unmigrated reader
- name any declared compatibility sidecars needed to preserve retained legacy
  fields for those unmigrated readers
- name the cutover gate and retirement gate for every affected bridge surface

Migration-wide rules:

- no consumer may read a bridge surface and a target product as peer
  authorities
- once a target product exists for an in-scope family, that target product is
  the authoritative persisted truth surface for that scope
- bridge surfaces that remain in use after that point are compatibility views
  only
- unchanged bridge outputs must remain reproducible from the authoritative
  target kernels during the compatibility window
- do not introduce a shared application assessment center as a migration
  shortcut; assessment behavior stays with the owning slice
- writer-only or scaffold-only commands are not current readers unless the
  current-state docs explicitly say they consume the persisted bridge artifact
  after it is written
- target readers must name a capability plus the authoritative product it reads;
  undocumented future package roots by themselves are not sufficient reader
  labels
- through the tax-first path, broader grouped or query surfaces stay on
  authoritative kernels, declared compatibility views, or tax-output-local and
  rendering-local derived outputs until a later capability-specific increment
  requires a dedicated derived read-model slice

The authoritative cutover matrix lives in
[Bridge To Target Mapping](../concepts/bridge-to-target-mapping.md).

## Canonical Current-Reader Inventory

Use these labels consistently in this page and in
[Bridge To Target Mapping](../concepts/bridge-to-target-mapping.md).

- `source normalize planner review and translation path`: planner-enabled
  normalization review and translation entry points that read
  `translation_input_candidates.json` and `translation_input_plan.json`
- `source assemble bridge projection path`: `source assemble` and its bridge
  projection flow that still builds assembled source datasets from
  `EconomicActivityDraft` and `SourceTranslationBatch`
- `operator review diagnostics`: operator review of normalization issues and
  reviews through `exceptions.csv`, `normalization_reviews.csv`, and related
  current diagnostics
- `reconciliation balances inspect`: the shared balance inspection capability
- `reconciliation balances check`: the deterministic balance-check capability
- `reconciliation balances summarize`: the shared balance summary capability
- `cointracking_csv rendering path`: the current CSV rendering path that emits
  `cointracking_csv`
- `dev-only oracle comparison path`: the dev-only oracle comparison tools and
  validation flows that compare current bridge outputs

## Landing Order

### 1. Contract Lock

Before broad implementation, freeze:

- target product contracts on
  [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md)
- ontology and ref seams on
  [Domain Ontology](../concepts/domain-ontology.md)
- shared gap and review contracts plus `SubjectRef`, `kernel_scope_id`, and
  readiness-locality rules on
  [Gap, Review, And Shared Attachment](../concepts/gaps-and-reviews.md)
- persistence, partitioning, and fast-path rules on
  [Reconciliation, Checkpoint, Journal, And Tax Architecture](../concepts/reconciliation-tax-architecture.md)
- bridge-to-target cutover rules on
  [Bridge To Target Mapping](../concepts/bridge-to-target-mapping.md)

Broad parallel implementation must not begin before those contract pages are
aligned and frozen.

### 2. Evidence And Claim Contract

The bounded
[`EvidenceSet -> ClaimSet`](../reference/evidence-claim-contract.md) contract.

Implemented posture:

- `EvidenceSet` becomes authoritative for in-scope evidence selection
- `ClaimSet` is the remaining upstream authority slice for in-scope
  evidence-local meaning
- `translation_input_plan.json`, `EconomicActivityDraft`, and
  `SourceTranslationBatch` survive only as derived compatibility views
- downstream bridge outputs remain on the live bridge path until the bounded
  economics/reconciliation/checkpoint contract makes the downstream target
  products authoritative for that scope

This evidence-and-claim contract is already implemented for the bounded
planner-enabled Coinbase slice.

### 3. Economics Reconciliation Checkpoint Contract

Land the bounded
[`EconomicFacts -> ReconciliationState -> Checkpoint`](../reference/economics-reconciliation-checkpoint-contract.md)
contract.

Required posture:

- `EconomicFacts` becomes authoritative for in-scope accepted economic meaning
- `ReconciliationState` becomes authoritative for in-scope continuity segments
  and balance targets
- `Checkpoint` becomes authoritative for in-scope accepted checkpoint truth
- `TransactionFact`, `balance_snapshots.csv`, and `balance_references.csv`
  survive only as derived compatibility views for unmigrated readers

This contract is therefore the first increment that converts
downstream bridge surfaces into target-derived compatibility views.

This contract is implemented for the bounded planner-enabled Coinbase slice.
Current facts, balance snapshots, and balance references remain on the
compatibility path for readers until the later reader-cutover work lands.

For that implemented downstream slice,
[Economics Reconciliation Checkpoint Contract](../reference/economics-reconciliation-checkpoint-contract.md)
holds the detailed downstream contract,
[Product Outputs](../workspace/working/products/README.md) owns current
workspace placement of authoritative kernels plus retained compatibility
views, and [Current State](current-state.md) owns the live runtime truth
statement. Keep future implemented-slice updates on those documents rather
than re-expanding completed downstream planning elsewhere.

### 4. Reader Cutovers

After those slices land, migrate readers one consumer surface at a time:

- evidence and claim readers move to target kernels first
- reconciliation and checkpoint readers move next
- balance inspect/check/summarize moves only when its application surface is
  explicitly repointed
- journal and tax readers move only after their upstream products are
  authoritative and stable
- broader grouped consumers stay on tax-output-local outputs, narrow rendering
  outputs, or compatibility views until a later capability-specific increment
  requires a dedicated derived read-model slice

### 5. Journal Contract

Land the bounded [Journal Contract](../reference/journal-contract.md) only
after authoritative `EconomicFacts` and `Checkpoint` exist for the relevant
scope.

Required posture:

- `Journal` becomes authoritative for in-scope journal entry expansion,
  repo-owned entry-check results, and journal-owned gaps
- `ledger_cli` is the first backend reader that consumes `Journal` directly
  through the declared journal backend seam
- new journal renderers, journal inspection outputs, and `ledger_cli` backend
  surfaces read `Journal` directly rather than rebuilding postings from
  compatibility facts or checkpoint helpers
- `cointracking_csv` and other current compatibility outputs remain on their
  existing compatibility path until a later cutover names them explicitly
- `TaxInputs` keep product identity and kernel meaning anchored to
  authoritative `Checkpoint` plus `EconomicFacts`; `Journal` does not become a
  hidden upstream product ref for tax

Cutover gates:

- deterministic `journal_id`, `entry_id`, `posting_id`, and `entry_check_id`
  are frozen for unchanged upstream products
- blocked journal mappings remain explicit through `EntryCheckRecord` rows,
  journal-owned gaps, and declared backend-local findings when the backend
  detects an additional downstream issue
- canonical journal replay and `ledger_cli` validation replay both run from
  authoritative `Journal` kernels alone
- no `journal_ref`, backend file hash, or backend-local id leaks into tax
  identity

### 6. TaxInputs And TaxOutputs

Land `TaxInputs` and `TaxOutputs` only after the upstream target products they
depend on are authoritative for the relevant scope and the journal increment
has stabilized entry-expansion plus entry-check ownership.

Rules:

- `TaxInputs` derive from authoritative `Checkpoint` plus `EconomicFacts`, not
  bridge facts, compatibility views, `Journal`, or a hidden `journal_ref`
- journal detail and journal-backend findings may inform downstream review
  posture only as declared non-authoritative detail
- `TaxOutputs` own selected-policy outputs, carry-forward rows, explicit
  unsupported-input rows, and the tax-output-local grouped readiness file for
  the active tax-first path only
- do not let tax decide source meaning, reconciliation completeness,
  checkpoint acceptance, or journal outcomes
- broader grouped consumers stay on tax-output-local outputs, narrow rendering
  outputs, or compatibility views until a later capability-specific increment
  requires a dedicated derived read-model slice

Cutover gates:

- repeated runs preserve `tax_inputs_id` and `tax_outputs_id` on unchanged
  authoritative upstream products plus selected tax-policy inputs
- unsupported tax posture stays explicit through `TaxUnsupportedInputRecord`
  rows and tax-owned gaps
- filing-critical tax outputs read `TaxOutputs` directly without bridge facts,
  CoinTracking tax reports, or journal-backend identity as peer authorities

### 7. Triggered Derived Read-Model Activation

The planning document may still carry later activation detail, but this page keeps the
durable rule: broader derived read models and projections stay deferred until
an implemented capability-specific increment actually needs them.

Before a trigger fires:

- keep reader cutovers on authoritative kernels or declared compatibility views
- do not introduce general read-model package roots or projection storage
  families early
- keep grouped derived outputs inside `TaxOutputs` or `application/rendering/`
  only when they remain exclusive to the active tax-first path

When a trigger fires:

- create only the specific capability-owned derived read-model package the new
  feature needs
- keep that derived surface additive and non-authoritative beside the
  authoritative pipeline products

## Bridge Retirement Rules

Retire or demote a bridge surface only when all of the following are true:

- the slice names one authoritative writer for the affected scope
- every active reader has a declared target reader or derived compatibility
  view
- parity and replay gates for the affected slice pass on unchanged evidence
- current-state docs are updated if the implemented live runtime surface
  changes

Bridge retirement is therefore:

- per scope, not global
- per reader, not just per writer
- controlled by cutover gates, not by naming preference

## Parity And Replay Gates

Do not retire an older path until all relevant gates pass:

- adapter or parser contract tests for the affected slice
- compatibility-view parity tests for every retained compatibility view
- target-kernel replay checks for the authoritative product
- reconciliation or checkpoint parity where the slice reaches those stages
- end-to-end smoke coverage for the affected workflow

When a compatibility view remains active, parity must prove:

- the view is reproducible from the authoritative target kernels
- the view preserves unchanged bridge behavior for unmigrated readers
- the view does not introduce new authority outside the target kernels

## Docs And Control-Plane Updates

When a migration slice changes architecture ownership or the live runtime
surface, update these pages together:

- [ROADMAP.md](../../ROADMAP.md)
- [Architecture Overview](../concepts/architecture-overview.md)
- [Bridge To Target Mapping](../concepts/bridge-to-target-mapping.md)
- [Current Bridge Contracts](../concepts/current-bridge-contracts.md) if live
  bridge truth changes
- the owning contract reference page when its contract changes

Current-state docs stay truthful to implemented behavior. Forward-looking docs
stay detailed enough that later implementation does not need to invent ids,
reader cutovers, storage placement, or gap/review/shared-attachment
boundaries.
Target naming governance remains catalog-first in this migration path: use one
machine-readable naming authority and keep the blocking `target-naming` check
on enforced forward-looking docs instead of re-encoding naming policy in
pytest or split doc checks.
