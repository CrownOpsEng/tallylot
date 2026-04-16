---
title: "Current Bridge Contracts"
summary: "Owning concept page for the live bridge contracts, bridge surfaces, and current schema rules."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 22
---

Use this page when you need the current runtime truth for the bridge that
exists today. This document owns the live bridge contracts and bridge-surface
rules.

The current bridge is real runtime behavior, not a historical footnote. It is
the active implementation boundary until later bounded increments replace it. At the
same time, it is not the final architecture center. Future stage contracts live
in [Pipeline Stage Contracts](pipeline-stage-contracts.md).

During migration, bridge compatibility views may remain valid runtime
surfaces for unmigrated readers, but they are never target contracts.

## Bridge Purpose And Limits

The live bridge currently centers on:

- `EconomicActivityDraft`
- `TransactionFact`
- `balance_snapshots.csv`
- `balance_references.csv`

That bridge is:

- the live implementation boundary
- the current delivery path
- the current parity baseline
- not the final architecture center

## Current Hard Runtime Rules

- raw evidence stays outside the repo
- normalization and profiling operate on one materialized raw capture root at a
  time
- planner-enabled adapters provide translation input candidates and the
  normalization flow selects the winning plan
- ambiguity blocks fact and balance artifact emission
- assembled source datasets are the reconciliation input
- provenance stays typed in runtime models and is flattened only at artifact
  boundaries
- operator-confirmed balance references may support runtime progress but do not
  satisfy filing-ready checkpoint requirements alone
- historical provider hydration remains separate from source adapters
- runtime balance artifacts are `balance_snapshots.csv` and
  `balance_references.csv`
- schema-version mismatch is resolved by regeneration, not compatibility
  wrappers

## Bridge Contract Surfaces

### `TransactionFact`

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

### `EconomicLeg`

Current bridge contract includes:

- `leg_id`
- `kind`
- `instrument_id`
- `quantity`
- optional `subtype`
- optional `attributed_to_leg_id`
- optional `location_id`

### `LegKind`

Current values:

- `primary`
- `charge`
- `rebate`
- `collateral`
- `settlement`
- `financing`
- `withholding`
- `adjustment`

### `FactLegPolicy`

Current bridge rules to preserve:

- per-kind limits
- signed-count constraints
- duplicate kinds prohibited
- zero-primary support only when intentionally allowed
- shared policy constants are part of the bridge contract

### Temporal Precision

Current rule to preserve:

- exact time uses UTC-aware `*_at`
- date-or-time uses `*_at` plus `*_precision`

### Schema Versioning

Current rule to preserve:

- fact artifacts are schema-versioned
- unknown schema versions fail fast
- regeneration from evidence is the recovery path

### `EconomicActivityDraft`

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

### `SourceTranslationBatch`

Current bridge bundle to preserve:

- drafts
- balance references
- balance reference issues
- issues
- reviews
- location inventory

## Current Schema And Artifact Contracts

### Repo-Wide Temporal Precision Contract

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

### Current Fact-Shape Contract

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

### Mixed Kernel Bridge Note

`TransactionFact` currently mixes computationally important fields, bridge
semantics, and bridge envelope detail in one record.

Computational kernel still carried today:

- `fact_id`
- `source`
- `adapter_id`
- `timestamp`
- `effective_at`
- `effective_precision`
- `location_id`
- `legs`
- `leg_policy`

Bridge semantic layer still carried today:

- `economic_kind`
- `projection_hint`
- `accounting_intent_hint`
- `tax_treatment_hint`

Bridge envelope and audit detail still carried today:

- `description`
- `provider_operation_key`
- `operation_group_id`
- `tx_hash`
- `raw_file`
- `raw_row_ref`
- `confidence`
- `status`

Rules:

- the current serializer persists all of these fields together because that is
  live bridge truth
- this mixed shape is not the target kernel rule for future products
- forward transformation rules and bounded proto-product mapping now live in
  [Bridge To Target Mapping](bridge-to-target-mapping.md)

### Bridge Fact Replay Fingerprint

For replay and parity checks on the first upstream slice, compiled bridge facts use one bridge
replay fingerprint contract.

Rules:

- fingerprint input is `[schema_version, ordered_fact_rows]`
- fact row order is `[timestamp, effective_at_or_null, fact_id]`
- leg order within each fact is `leg_id`
- include `fact_id`, identity fields, time fields, participant fields,
  semantic fields, `legs`, `FactLegPolicy`, and `status`
- exclude `description`, `raw_file`, `raw_row_ref`, `confidence`,
  `fact_annotations.json`, and other bridge sidecars
- serialize as stable UTF-8 JSON with stable object-key order and SHA-256
  hashing

### Current Normalization Window Contract

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

### Capture And Assembly Contract

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
  union of primary evidence, collapses exact semantic duplicates, and
  surfaces semantic conflicts explicitly
- location inventory and balance evidence provenance reference captures by
  `capture_uid`, with human-readable labels and roots treated as optional
  report fields rather than as the key

### Transitional Adapter Draft Seam

Source normalization currently translates through `EconomicActivityDraft`
before shared bridge fact compilation.

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
  CoinTracking rows or other output-adapter shapes directly
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

## Bridge-To-Target Direction

- keep current bridge names in current-state docs and live bridge code until a
  later implementation slice replaces them
- document future target products and ontology on their owning pages rather
  than mutating current bridge pages into a blended current-and-future hybrid
- treat this bridge as the active runtime seam that later target slices must
  replace cleanly, not as a structure that should be immortalized
- use [Bridge To Target Mapping](bridge-to-target-mapping.md) as the single
  authority for how these bridge seams land in bounded proto-products during
  migration
