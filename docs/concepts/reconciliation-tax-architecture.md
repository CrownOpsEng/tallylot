---
title: "Reconciliation And Tax Architecture"
summary: "Design anchor for the current bridge, final pipeline products, performance rules, and filing-critical rollout."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 20
---

This document is the implementation anchor for evolving the repo away from
tracker-dependent historical workflows and into an independent reconciliation,
checkpoint, accounting, and tax runtime.

Use it when making structural decisions that affect normalization,
reconciliation, checkpointing, journaling, or tax computation. Treat it as a
design contract, not as a loose idea list.

## Current Runtime Note

Current runtime truth remains:

- typed application architecture under `src/tallylot/`
- CLI and library only
- filesystem-backed active storage
- SQLite deferred behind interfaces and ports
- provider-backed AI deferred behind interfaces and ports
- raw evidence outside the repo in the external workspace

The filing-critical output horizon remains `2023` through `2025`.

The system must:

- establish one source-backed, balance-confirmed checkpoint near `2026-03-23`
- use the `2023-08-05` CoinTracking export set as a historical oracle, not a
  hard checkpoint
- compute forward tax state for `2023` to `2025`
- render a deterministic double-entry journal and require it to validate
- surface unsupported or ambiguous truth as explicit issues, reviews, and gaps
- preserve one interface-neutral application surface so future CLI, HTTP, API,
  and agent entrypoints can share the same typed workflows

Normal runtime operation must stay platform-agnostic:

- raw source exports, wallet statements, and checkpoint evidence are the normal
  reconstruction inputs
- CoinTracking is one ordinary output adapter and one optional oracle family
  for dev-only comparison workflows
- CoinTracking tax and accounting reports are oracle-only support artifacts for
  comparison and regression, not normal runtime dependencies
- the internal engine should stay asset-class-agnostic so crypto, FX,
  securities, and similar surfaces can remain adapter- and policy-driven

## Active Bridge Note

The current runtime bridge centers on:

- `EconomicActivityDraft`
- `TransactionFact`
- `balance_snapshots.csv`
- `balance_references.csv`

That bridge is:

- the live implementation seam
- the current delivery path
- the current parity baseline
- not the final architecture center

Current operational surfaces that remain part of runtime truth:

- capture-scoped source profiling
- capture-scoped normalization
- planner-enabled normalization
- translation input candidates, plan, and blocking issues
- source assembly into `working/normalized/sources/<source>/`
- shared statement extraction
- statement-backed balance references
- checkpoint-owned manual balance submission scaffolding and validation
- checkpoint location inventory rebuild
- offline-by-default balance inspection and checking
- optional provider hydration through separate balance-provider adapters
- replay validation
- oracle comparison and verification workflows

### Current Hard Runtime Rules

- raw evidence stays outside the repo
- normalization and profiling operate on one materialized raw capture root at a
  time
- planner-enabled adapters provide translation input candidates and the core
  selects the winning plan
- ambiguity blocks fact and balance artifact emission
- assembled source datasets are the reconciliation input surface
- provenance stays typed in runtime models and is flattened only at artifact
  boundaries
- operator-confirmed balance references may support runtime progress but do not
  satisfy filing-ready checkpoint requirements alone
- historical provider hydration remains separate from source adapters
- runtime balance artifacts are `balance_snapshots.csv` and
  `balance_references.csv`
- schema-version mismatch is resolved by regeneration, not compatibility
  wrappers

### Current Bridge Contracts

#### `TransactionFact`

Current bridge contract includes:

- identity:
  - `fact_id`
  - `source`
  - `adapter_id`
  - `provider_operation_key`
  - `operation_group_id`
  - `tx_hash`
- time:
  - `timestamp`
  - optional `effective_at`
  - optional `effective_precision`
- participants:
  - `location_id`
- semantics:
  - `economic_kind`
  - `accounting_intent_hint`
  - `tax_treatment_hint`
  - optional `projection_hint`
- economics:
  - `legs`
  - `FactLegPolicy`
- metadata and status:
  - `description`
  - `raw_file`
  - `raw_row_ref`
  - `confidence`
  - `status`

#### `EconomicLeg`

Current bridge contract includes:

- `leg_id`
- `kind`
- `instrument_id`
- `quantity`
- optional `subtype`
- optional `attributed_to_leg_id`
- optional `location_id`

#### `LegKind`

Current values:

- `primary`
- `charge`
- `rebate`
- `collateral`
- `settlement`
- `financing`
- `withholding`
- `adjustment`

#### `FactLegPolicy`

Current bridge rules to preserve:

- per-kind limits
- signed-count constraints
- duplicate kinds prohibited
- zero-primary support only when intentionally allowed
- shared policy constants are part of the bridge contract

#### Temporal Precision

Current rule to preserve:

- exact time uses UTC-aware `*_at`
- date-or-time uses `*_at` plus `*_precision`

#### Schema Versioning

Current rule to preserve:

- fact artifacts are schema-versioned
- unknown schema versions fail fast
- regeneration from evidence is the recovery path

#### `EconomicActivityDraft`

Current bridge responsibilities to preserve:

- stable draft identity
- timestamp and temporal precision
- location scope
- `legs`
- `FactLegPolicy`
- provider operation key
- grouped-row support
- layered hints
- provenance refs
- review markers
- confidence and status

#### `SourceTranslationBatch`

Current bridge bundle to preserve:

- drafts
- balance references
- balance reference issues
- issues
- reviews
- location inventory

### Current Schema And Artifact Contracts

#### Repo-Wide Temporal Precision Contract

- use one timing convention everywhere in the repo:
  - exact-time fields use UTC-aware `*_at`
  - fields that may be date-only or exact-time use `*_at` plus `*_precision`
- `*_precision` uses one shared enum with at least:
  - `timestamp`
  - `date`
- date-only values are stored distinctly from exact timestamps even when an
  exact timestamp falls at midnight
- adapters are responsible for preserving this distinction at translation time
- infer precision from the source contract and parsed field shape, not from the
  normalized clock value

#### Current Fact-Shape Contract

- `TransactionFact` and `EconomicActivityDraft` use one shared `legs` tuple
- fact construction requires successful identifier resolution to exactly one
  `InstrumentId`
- unresolved or ambiguous identity must emit review output and a blocking issue
  rather than guessing
- every leg carries:
  - stable `leg_id`
  - signed `quantity`
  - semantic `LegKind`
  - optional adapter-detail `subtype`
  - optional `attributed_to_leg_id` metadata
- signed quantities use one meaning everywhere:
  - positive increases the balance of the leg location
  - negative decreases the balance of the leg location
- `attributed_to_leg_id` is valid only on non-`primary` legs and only when it
  references one concrete leg in the same fact
- `FactLegPolicy` is generic and per-kind:
  - `LegShapeLimit` declares `min_count`, `max_count`, `min_positive_count`,
    `max_positive_count`, `min_negative_count`, and `max_negative_count`
  - no duplicate kinds
  - minimum counts cannot exceed maximum counts
  - signed-count limits cannot exceed per-kind totals
  - unspecified kinds are disallowed
  - zero-`primary` shapes are opt-in through the declared policy
- current shared policy constants cover:
  - single-primary activity
  - two-sided primary exchange
  - two-sided primary exchange with one `charge`
- CoinTracking currently supports only:
  - at least one `primary`
  - up to one positive `primary`
  - up to one negative `primary`
  - up to one negative `charge`
  - no other non-primary leg kinds
  - renderers derive inbound and outbound adapter concepts from sign

#### Current Normalization Window Contract

- runtime timestamps are timezone-aware UTC in drafts, facts, balance
  snapshots, and balance references
- persisted artifact timestamp text remains `YYYY-MM-DD HH:MM:SS` and is
  interpreted as UTC on read
- fields that may be date-only or exact-time persist both `*_at` and
  `*_precision`
- `facts.csv` is schema-versioned and readers fail fast on unexpected
  `schema_version` values
- `balance_snapshots.csv` and `balance_references.csv` persist `instrument_id`
  values and use `target_at` plus `target_precision`; balance references also
  persist `observed_at` plus `observed_precision`
- cross-source balance corroboration is additive in the first release
- windowed normalization applies to:
  - `facts.csv`
  - `fact_annotations.json`
  - `balance_snapshots.csv`
  - `exceptions.csv`
  - `normalization_reviews.csv`
- windowed normalization does not apply to:
  - `balance_references.csv`
  - `location_inventory.csv`
- source-scope portfolio evidence that does not itself prove wallet ownership
  may contribute balance evidence only under constrained same-source same-chain
  rules and must remain explicitly caveated
- review records carry `context_timestamp`, dataset-level untimed reviews stay
  visible when a window is active, and summaries report
  `reviews_outside_normalization_window`

#### Capture And Assembly Contract

- raw capture roots use `evidence/raw/source/<source>/<capture_label>/`
- capture metadata stores the stable `capture_uid`, intake timestamps,
  manifest fingerprint, and workspace-relative refs
- untouched upstream originals stay under the raw capture root
- `working/supporting_artifacts/` is limited to derived or operator-authored
  helper material
- capture-normalized outputs live under
  `working/normalized/captures/<capture_uid>/`
- assembled source outputs live under `working/normalized/sources/<source>/`
- source assembly merges accepted captures deterministically, preserves the
  union of source-backed evidence, collapses exact semantic duplicates, and
  surfaces semantic conflicts explicitly
- location inventory and balance evidence provenance reference captures by
  `capture_uid`, with human-readable labels and roots treated as optional
  report fields rather than as the key

#### Transitional Adapter Draft Seam

Source normalization should translate through `EconomicActivityDraft` until all
adapters emit `TransactionFact` artifacts directly.

Required draft responsibilities:

- stable identity claims plus evidence references
- UTC-aware timestamp and provenance
- optional `effective_at`
- optional `effective_precision`
- account and wallet scope
- one shared `legs` tuple only; no separate fee lane
- explicit leg semantics per leg:
  - stable `leg_id`
  - `LegKind`
  - optional `subtype`
  - optional `attributed_to_leg_id` on non-`primary` legs only
- explicit per-kind leg-shape policy through `FactLegPolicy` and
  `LegShapeLimit`, including any required minimum counts
- provider operation key and grouped-row support
- layered classification hints:
  - economic kind
  - projection type
  - journal intent
  - tax treatment code
- explicit review or ambiguity markers

Rules:

- provider modules translate into drafts only; they do not assemble
  CoinTracking rows or other output-adapter payloads directly
- shared identifier resolution must succeed to exactly one instrument before
  fact construction
- unresolved or ambiguous identifier resolution blocks fact emission for the
  affected activity and must surface both review output and a blocking issue
- shared fact builders may derive `TransactionFact` objects from drafts, but
  that derivation stays in shared support rather than provider-local code
- shared support stays adapter-agnostic and registry-driven
- draft-only provenance references and review markers must survive compilation
  through a fact-keyed sidecar artifact instead of being dropped
- one shared projection mapper owns the mapping from layered classifications
  into concrete output-adapter row types
- grouped operations and provider-local export families must resolve through
  explicit translation registries, not ad hoc adapter entry-point branching

## Final Naming Mapping Note

Forward-looking architecture and rollout docs use these final names:

| Current target-doc term | Final term |
| --- | --- |
| `EvidenceBundle` | `EvidenceSet` |
| `ClaimBundle` | `ClaimSet` |
| `EconomicDataset` | `EconomicFacts` |
| `ReconciliationDataset` | `ReconciliationState` |
| `CheckpointPackage` | `Checkpoint` |
| `JournalDataset` | `Journal` |
| `TaxDeterminantDataset` | `TaxInputs` |
| `TaxOutputDataset` | `TaxOutputs` |

Current bridge and status docs may continue using current implementation terms
where accuracy requires them. Target architecture docs should use the final
names after the mapping is established.

Target-direction internal rename guidance:

| Current bridge term | Target-direction name |
| --- | --- |
| `EconomicActivityDraft` | `ActivityClaim` |
| `EconomicLegDraft` | `LegClaim` |
| `ActivityDraftSeed` | `ActivitySeed` |
| `TransactionFact` | `EconomicEvent` |
| `FactSemantics` | `ClassificationHints` |
| `FactLegPolicy` | `LegPolicy` |
| `LegShapeLimit` | `LegCountLimit` |
| `EconomicKind` | `EventKind` |
| `ProjectionHint` | `OutputHint` |
| `AccountingIntentHint` | `AccountingHint` |
| `TaxTreatmentHint` | `TaxHint` |
| `SourceTranslationBatch` | `TranslationResult` |

These are target-direction names, not claims that the current code already uses
them.

## Target Pipeline Products And Stage Meanings

The target runtime pipeline is:

`EvidenceSet -> ClaimSet -> EconomicFacts -> ReconciliationState -> Checkpoint -> Journal -> TaxInputs -> TaxOutputs`

Design rules:

- upstream stages preserve optionality
- downstream stages force specificity only when they own the decision
- no stage may guess a later-stage answer
- no stage may suppress uncertainty that a later stage must still see
- no stage may duplicate upstream semantic payloads unless the meaning has
  changed

### `EvidenceSet`

Purpose:

- deterministic intake output before semantic commitment

Contains:

- selected source artifacts
- source-local parsed observations
- provenance
- document, statement, and inventory observations
- selected, superseded, and blocked alternatives
- deterministic selection decisions

Must guarantee:

- deterministic selection
- stable provenance and locators
- no forced economic meaning
- no forced reconciliation, accounting, or tax decisions

### `ClaimSet`

Purpose:

- source-local meaning layer before economic truth is fixed

Contains:

- activity claims
- balance claims
- ownership claims
- location claims
- instrument claims
- contract claims
- valuation claims
- candidate interpretations
- claim-owned issues and reviews

Must guarantee:

- source-local semantics only
- preserved ambiguity where one safe final interpretation is unavailable
- provenance for every claim

Must not:

- force unresolved meaning into final economic or policy interpretations

### `EconomicFacts`

Purpose:

- economic truth the system can safely assert

Contains:

- economic events
- economic legs
- instrument identity
- contract identity where relevant
- position identity where relevant
- owner and counterparty identity where known
- temporal precision
- settlement and supersession links
- valuations
- confidence and ambiguity markers

Must support:

- holdings movements
- cash movements
- obligations and rights
- settlements
- collateral changes
- financing flows
- fees, rebates, and withholding
- corrections and supersession chains
- corporate actions
- restructurings
- lifecycle-heavy activity

Must not:

- collapse to spot-trade assumptions
- let output hints drive core behavior

### `ReconciliationState`

Purpose:

- completeness, linkage, continuity, checkpoint candidates, and
  reconciliation-owned gaps

Contains:

- transfer links
- balance targets and assertions
- continuity windows
- missing funding and settlement legs
- unresolved ownership transitions
- corroboration sidecars
- checkpoint candidates
- reconciliation-owned gaps
- readiness slices

Must guarantee:

- explicit completeness decisions
- explicit continuity decisions
- explicit missing-leg and missing-evidence surfaces
- preservation of partial truth when the whole window is not yet clean
- no rewriting of upstream truth to satisfy checks

### `Checkpoint`

Purpose:

- accepted checkpoint truth and acceptance basis

Contains:

- accepted checkpoint assertions
- adopted opening state when intentionally used
- supporting evidence and provenance
- continuity decisions into accepted state
- trust level and acceptance basis

Must guarantee:

- accepted checkpoint truth is first-class
- source-backed evidence remains preferred
- operator assertions do not silently become filing-ready checkpoint truth

### `Journal`

Purpose:

- accounting expansion and validation

Contains:

- journal entries and postings
- provenance back to accepted upstream truth
- validation results
- accounting-owned gaps

Must guarantee:

- deterministic posting expansion
- explicit validation
- explicit unsupported accounting coverage

Must not:

- become a truth repair layer

### `TaxInputs`

Purpose:

- policy-ready, jurisdiction-neutral tax input surface

Contains:

- acquisitions
- dispositions
- income events
- financing costs
- internal transfers
- corporate actions
- tax-relevant valuations
- basis or pool state transitions
- tax-owned unresolved items

Must guarantee:

- jurisdiction-neutral determinants
- explicit basis-affecting state changes
- explicit tax-owned blockers where upstream truth is not tax-complete

### `TaxOutputs`

Purpose:

- one selected tax policy's outputs

Contains:

- summaries
- forms and schedules
- carry-forward state
- unsupported or deferred outputs
- policy-specific notes

Must guarantee:

- outputs are derived from `TaxInputs` through selected tax policies
- outputs are never described as coming directly from `EconomicFacts` or
  `ReconciliationState`

## Shared Cross-Stage Contracts

These contracts should be defined once and reused everywhere.

### Provenance

Use one typed provenance model.

Rules:

- typed in runtime models
- flattened only at artifact boundaries
- file and member identity kept separate from row and page anchors
- capture identity kept separate from display labels and file paths

### Gaps

Use one shared gap model.

Minimum fields:

- `gap_id`
- `owner_stage`
- `blocking_for_stage`
- `subject_ref`
- `gap_kind`
- `known_facts`
- `missing_inputs`
- `candidate_interpretations`
- `required_evidence`
- `allowed_resolution_methods`
- `recommended_next_action`
- `confidence`
- `materiality`
- `provenance_refs`

Minimum taxonomy:

- `missing_evidence`
- `unresolved_identity`
- `unresolved_linkage`
- `contradiction`
- `policy_required_determination`
- `operator_override_required`

### Readiness

Use one exact readiness vocabulary:

- `semantic_ready`
- `reconciliation_ready`
- `checkpoint_ready`
- `accounting_ready`
- `tax_ready`

Readiness is sliceable by:

- source
- location
- instrument
- subject ref
- continuity segment
- checkpoint date
- tax year where relevant

Rules:

- this exact slice definition must stay identical everywhere it appears
- when a stage needs to distinguish `Contract` from `Position`, it must do so
  explicitly through the referenced `SubjectRef`
- dataset readiness is derived from subject-level reducers, not stored as the
  only truth

### Identity

Keep these identity seams separate:

- instrument identity
- contract identity
- position identity
- location identity
- legal owner identity
- beneficial owner identity
- counterparty identity

### Valuation

Valuation is first-class.

Fields:

- amount
- currency
- purpose
- timestamp
- precision
- source
- confidence
- provenance

### Checkpoint Assertions

Use one shared checkpoint-assertion vocabulary across reconciliation,
checkpoints, accounting, and tax.

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

Storage implication:

- this structure maps cleanly to future database storage
- first-class records become base tables
- sidecars become linked tables keyed by stable ids
- flattening belongs to storage and export codecs
- runtime models remain typed and normalized

## Performance And Calculation-Path Rules

The core pipeline must stay auditable, deterministic, replayable, and fast
enough for large-scale calculation.

### Hot Path

Inner-loop calculations for:

- reconciliation
- checkpoint continuity
- journal validation
- tax computation

must operate on compact typed records only.

Hot-path data should include:

- event ids
- timestamps and effective times
- subject refs
- location refs
- instrument refs
- signed quantities
- explicit link ids
- explicit state transitions
- valuations where computation requires them
- minimal classification hints only where needed

The hot path should not repeatedly join in:

- full provenance detail
- review records
- large issue text
- evidence metadata blobs
- renderer metadata
- adapter-local annotations that do not change computation

Those belong in sidecars and explanation layers.

### Deterministic Ordering

Reducers must use stable ordering:

- effective time when present
- otherwise event timestamp
- then deterministic tie-break keys such as source sequence, event id, or leg
  id

Rules:

- reducers must be deterministic
- replay must be consistent across runs
- ordering must not depend on incidental file order

### Partitioning

Expensive processing must be partitionable by:

- source
- location
- instrument
- subject ref
- continuity segment
- checkpoint date
- tax year where relevant

These same partition keys are the basis for efficient recalculation. The system
should rerun affected slices instead of replaying everything.

### Materialized State And Snapshots

Materialized state is allowed and encouraged where replay cost would otherwise
become too high.

Minimum materialization surfaces:

- checkpoint state snapshots
- reconciliation continuity summaries
- position state snapshots where replay cost is material
- tax pool and carry-forward state by tax year
- validated posting aggregates where useful

Rules:

- materialized state is derived and replaceable
- it does not replace source-of-truth history
- it exists to keep calculation cost bounded

### Reducer Design Rules

Prefer:

- linear or near-linear reducers over sorted subject streams
- explicit link records instead of repeated inference
- one-time normalization of ambiguous bridge data into later-stage structures
- reuse of prior state outputs when valid

Avoid:

- repeated global joins across the full history
- repeated scanning of unrelated sources or years
- repeated evidence-level parsing during later-stage calculations
- dynamic policy dispatch inside tight per-record loops

### Tax Performance Rules

Tax calculation should not recompute full acquisition history from scratch for
every output row if bounded state is available.

The design should support:

- tax-year partitioning
- carried-forward pool and state materialization
- determinant grouping by subject and tax year
- reuse of prior year-close state as next year-open state

Policy selection should be resolved before execution, not as dynamic branching
inside the hot loop.

## Generic Core Requirements

The core runtime must remain instrument-agnostic, source-agnostic,
output-agnostic, and storage-neutral.

Rules:

- CoinTracking is an edge import, export, and oracle surface, not a runtime
  dependency
- crypto is the current filing scope, not the ontology center
- persistence implements the model; it does not define the model
- no wrapper lanes, compatibility shims, or legacy parallel runtime models
  should survive after a clean replacement is ready
- refactors should replace old structures cleanly when the new structure is
  ready
- tests and parity must be preserved or strengthened through refactors

## Ontology And Identity Seams

The future model should use this ontology explicitly.

### Core Business Concepts

- `Instrument`
- `Position`
- `Contract`
- `Location`
- `LegalOwner`
- `BeneficialOwner`
- `Counterparty`
- `EconomicEvent`
- `EconomicLeg`
- `SettlementState`
- `LifecycleEvent`
- `Valuation`
- `CheckpointAssertion`
- `Posting`
- `TaxInput`
- `Gap`
- `Readiness`

### `Contract` Versus `Position`

Do not collapse `Contract` and `Position`.

- `Contract` is a specific agreement instance with terms
- `Position` is an economic exposure or holding state that may arise from one
  contract, many contracts, or no explicit contract

### `SubjectRef`

Use `SubjectRef` only for shared cross-stage infrastructure that needs a
generic pointer.

Minimum fields:

- `subject_kind`
- `subject_id`

Initial supported `subject_kind` values:

- `position`
- `contract`

Rules:

- use `Contract` and `Position` explicitly in business logic and modeling
- use `SubjectRef` only where shared infrastructure needs a generic pointer
- do not use `SubjectRef` as an excuse to stop modeling the true concept

### Bridge Classifications Versus The Final Ontology

Current bridge classifications remain real and important, but they are not the
full ontology.

Rules:

- current bridge classifications matter now
- they remain valid bridge and rendering hints
- they are not the long-term center of the model
- future support for broader financial instruments should be driven by the core
  ontology, not by activity-label expansion alone

## Source, Output, Oracle, And Persistence Boundaries

### Source Boundaries

- source adapters produce source-local evidence and claims
- adapters may emit safe bridge hints only
- adapters do not own reconciliation
- adapters do not own checkpoint acceptance
- adapters do not own accounting
- adapters do not own tax policy

### Output Boundaries

- renderers consume downstream-owned products
- renderer-specific constraints stay at the edge
- CoinTracking row rules remain output-adapter concerns only

### Oracle Boundaries

- CoinTracking import and export shapes may be supported at the edge
- CoinTracking reports remain oracle-only
- oracle parsing remains outside `src/tallylot/`
- the system must still reconstruct, reconcile, checkpoint, journal, and
  compute taxes if CoinTracking tax reports disappear

### Crypto Boundaries

- crypto is the current filing scope
- crypto is not the ontology center
- crypto-specific language belongs at adapter, policy, or output edges unless
  fundamentally required
- the core remains broad enough for non-crypto support later

### Persistence Boundaries

- persistence implements the model
- persistence does not define the model
- no core runtime type relies on filesystem path, CSV row order, or export
  shape as identity
- raw evidence remains file-backed even after future database adoption
- repository ports remain the persistence seam
- active SQLite rollout is deferred until after the filing-critical path is
  stable

## Tax Policy Architecture

Typed tax-policy selection is a foundation seam, not an afterthought.

### Required Contracts

- `TaxPolicyId`
- `TaxPolicyDescriptor`
- `TaxPolicy`
- `TaxPolicyRegistry`
- `ApplyTaxPoliciesRequest`
- `ApplyTaxPoliciesResponse`

### `TaxPolicyDescriptor`

Must include:

- stable id
- display name
- jurisdiction or regime code
- supported years or periods
- supported output families
- version
- limitations
- status:
  - `supported`
  - `partial`
  - `experimental`
  - `deferred`

### `TaxPolicy`

Consumes:

- one `TaxInputs`
- one execution context

Produces:

- one `TaxOutputs`
- tax-owned gaps
- unsupported or deferred outputs

### Selection Semantics

- one run may select one or more policy ids
- all selected policies run independently against the same input set
- one policy's unsupported coverage does not invalidate another's results
- unknown policy ids fail request validation immediately
- missing explicit selection and missing configured default also fail
  validation
- configured defaults live only at application, config, and interface
  boundaries
- the core must not assume one default jurisdiction

### Tax-Stage Ownership

Tax policy may decide:

- jurisdiction-specific treatment
- basis rules
- carry-forward rules
- output structure

Tax policy may not decide:

- source meaning
- economic truth
- reconciliation truth
- checkpoint truth
- accounting truth

### MVP Tax Scope

- keep the seam general
- implement Canada MVP first
- prioritize the filing path for `2023`, `2024`, and `2025`
- do not build a plugin platform

## Package Ownership Guidance

Keep package ownership direct and stage-oriented.

Suggested long-term ownership:

- `domain/evidence/`
  - evidence observations, provenance primitives, and evidence-selection ids
- `domain/claims/`
  - source-local claim types and claim-owned ambiguity surfaces
- `domain/economics/`
  - economic events, legs, valuations, settlement, and lifecycle state
- `domain/reconciliation/`
  - links, continuity, readiness reducers, and checkpoint candidates
- `domain/checkpoints/`
  - checkpoint assertions, acceptance basis, and adopted opening state
- `domain/accounting/`
  - journals, entries, postings, and validation outputs
- `domain/tax/`
  - tax inputs, policy contracts, carry-forward state, and outputs

Application ownership:

- `application/intake/`
  - capture planning, apply, and evidence selection
- `application/evidence/`
  - shared statement extraction and provenance locator handling
- `application/profiling/`
  - capture profile construction, inventory inspection, and timezone review
- `application/normalization/`
  - evidence-to-claim translation planning and bridge artifact production
- `application/normalization/assembly/`
  - deterministic merge of accepted capture outputs into assembled source
    datasets
- `application/reconciliation/`
  - links, continuity, gaps, readiness, and checkpoint candidates
- `application/checkpoints/`
  - checkpoint evidence assembly, manual balance submission validation, and
    checkpoint acceptance
- `application/accounting/`
  - journal expansion, validation, and summaries
- `application/tax/`
  - tax-input assembly, policy selection, and tax-output rendering
- `application/outputs/`
  - downstream renderer orchestration

Boundary rules:

- `interfaces/` orchestrates services only
- `infrastructure/` implements ports
- `application/` depends on domain and ports
- `domain/` has no infrastructure imports

## Rollout Summary Aligned With The Roadmap

### Phase 0. Shared Foundations

Deliver:

- shared provenance family
- shared gap model and taxonomy
- shared readiness model and reducers
- shared checkpoint-assertion vocabulary
- explicit identity seams
- `SubjectRef`
- tax-policy selection contracts
- alignment across architecture, roadmap, and migration docs

Rules:

- treat these as blocking shared foundations
- do not let each stage invent its own blocker or status surface

### Phase 1. Evidence And Claims

Deliver:

- formal `EvidenceSet`
- formal `ClaimSet`
- deterministic selection outputs
- explicit selected, superseded, and blocked evidence outputs
- explicit claim ambiguity rules
- oracle reader contracts remain outside runtime
- current output alias normalization where needed

Rules:

- current bridge remains active
- do not introduce wrapper lanes
- do not force ambiguous source rows into final facts prematurely

### Phase 2. Fact-Path Follow-Through

Deliver:

- claim-to-economic compilation seam
- continued use of `TransactionFact` as the row-level bridge until replacement
  is ready
- adapter stabilization on current contracts
- planner artifacts before translation:
  - candidates
  - plan
  - blocking issues
- shared provenance locator family at artifact boundaries
- semantic and replay parity checks for unchanged evidence

Rules:

- direct fact artifacts remain the only active runtime model
- no parallel compatibility models
- clean schema breaks are allowed when replacement is ready
- unknown schema versions fail fast and recover by regeneration

### Phase 3. Reconciliation

Deliver:

- exact balance assertion stability
- transfer links
- continuity windows
- reconciliation-owned gaps
- readiness slices
- checkpoint candidates
- corroboration sidecars
- deterministic correction handling
- independence from raw capture layout

Rules:

- reconciliation consumes facts plus checkpoint evidence
- exact balance assertions are one surface, not the whole reconciliation
  product
- readiness must use the full shared slice definition

### Phase 4. Checkpoints

Deliver:

- typed checkpoint contracts
- checkpoint evidence requirements
- manual balance submission as typed checkpoint-owned input
- trust level and acceptance basis
- checkpoint continuity reports
- intentional opening-state adoption with provenance

Rules:

- operator-confirmed balances may support runtime progress
- filing-ready checkpoints still require source-backed support

### Phase 5. Accounting

Deliver:

- internal journal model
- renderer port
- Ledger CLI renderer
- validation result artifacts
- accounting-owned gaps
- accounting summaries tied to reconciliation and checkpoints

Rules:

- accounting expands and validates accepted truth
- accounting does not repair truth

### Phase 6. Tax Inputs And First Policy

Deliver:

- `TaxInputs`
- tax-policy registry and selection
- Canada MVP policy
- pooled ACB state
- disposition outputs
- income outputs
- carry-forward and year summaries
- unsupported tax-item outputs
- tax-owned unresolved items

Rules:

- tax outputs flow from inputs through policy
- remove wording that says tax outputs come directly from reconciled facts
- tax inputs must be reproducible from reconciled economics plus accepted
  checkpoint truth

### Phase 7. Filing Workflow

Deliver:

- end-to-end filing workflow
- checkpoint continuity gate
- oracle comparison against historical CoinTracking outputs
- explicit deferred-case capture
- reproducible `2023`, `2024`, and `2025` outputs from workspace evidence

### Phase 8. Transition Retirement And Later Storage

Deliver later:

- retirement of transition-only assumptions
- broader policy coverage
- SQLite-backed repositories behind existing ports
- no semantic-model rewrite as part of storage rollout

## Filing-Critical Acceptance Criteria

The system is filing-ready only when all of these are true:

- a source-backed checkpoint exists near `2026-03-23`
- no unresolved material reconciliation issues remain
- no unresolved material unsupported tax items remain
- Ledger CLI validation passes for supported activity
- the forward-computed state from the `2023-08-05` historical oracle lands on
  the source-backed checkpoint
- `2023`, `2024`, and `2025` outputs can be reproduced from workspace evidence

## Materiality And Unsupported Cases

Default materiality rules:

- do not silently suppress any non-zero drift
- log every difference
- allow explicit immaterial waivers only in artifacts, never in code comments
- default immaterial threshold: `<= CAD 25` per asset and `<= CAD 250`
  aggregate
- do not auto-waive `CAD`, `BTC`, `ETH`, or stablecoins

Unsupported or ambiguous truth must produce explicit outputs and roadmap items.
Do not guess on:

- superficial loss treatment
- capital versus business account classification
- unsupported DeFi lifecycle cases
- NFTs
- bankruptcy or scam-loss workflows

## External Library Policy

Use directly when they are permissive and fit cleanly:

- Ledger CLI as the first journal validator
- RP2 as an architectural reference or narrow comparison source
- `tsiemens/acb` as a scenario and formula reference
- small MIT or Apache libraries only when the reuse is narrow and documented

Use for reference only:

- Beancount
- hledger
- GPL codebases, tests, or examples

Do not:

- copy GPL code into the repo
- lightly rewrite GPL implementations and treat them as original
- introduce heavy support libraries that fight the current typed architecture

## Tests To Add

### Schema And Parsing

- multi-leg transaction parsing
- valuation provenance validation
- CoinTracking alias normalization
- correction and supersession chains

### Reconciliation

- transfer pairing across owned wallets and exchanges
- exact balance assertion workflow over unified balance targets with
  `source_document` precedence, optional `network_api` hydration, and
  `operator_assertion` fallback
- redistribution corrections
- checkpoint balance assertions
- forward continuity from oracle boundary to checkpoint

### Accounting

- journal posting generation
- Ledger CLI parse and balance
- supported commodity balances matching checkpoint outputs

### Tax

- pooled ACB updates
- crypto-to-crypto dispositions
- fee treatment in quote, base, and third asset
- staking and reward income
- derivatives and margin realized PnL
- explicit unsupported-item logging

## Initial Refactor Guidance

Perform only the refactors required to support the new architecture:

- split new domain concepts into dedicated packages rather than expanding
  `domain/transactions/` or sibling domain capability packages
- promote workflow helper clusters into a package once a third related sibling
  would otherwise be added
- introduce transaction facts before expanding tax services
- replace normalized transaction artifacts directly while migrating downstream
  services
- remove normalized-transaction-first workflows once fact consumers land

Do not:

- add SQLite first
- add a web UI
- add generic workflow engines
- re-centralize business rules in adapters
- keep pushing new semantics into one `category` string

## Time Summary

AI-assisted estimate for the filing-critical path:

- `106` to `164` hours

AI-assisted estimate including open-source hardening:

- `126` to `196` hours

Those ranges assume focused implementation with the current repo standards,
tests, and documentation discipline preserved.
