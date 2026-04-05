---
title: "Reconciliation And Tax Architecture"
summary: "Design anchor for the provider-neutral reconciliation, accounting, checkpoint, and tax system."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 20
---

This document is the implementation anchor for evolving the repo away from
tracker-dependent historical workflows and into an independent reconciliation,
accounting, and Canadian tax computation system.

Use this plan when making structural decisions that affect normalization,
checkpointing, journaling, or tax computation. Treat it as a design contract,
not as a loose idea list.

## Objective

Deliver a filing-ready `2023` to `2025` workflow without treating CoinTracking
as a required runtime ledger or organizing model, while preserving the repo's
current typing, layering, and evidence discipline.

The system must:

- establish one source-backed, balance-confirmed checkpoint near `2026-03-23`
- use the `2023-08-05` CoinTracking export set as a historical oracle, not a
  hard checkpoint
- compute forward tax state for `2023` to `2025`
- render a deterministic double-entry journal and require it to validate
- surface unsupported or ambiguous facts as explicit issues
- preserve one interface-neutral application surface so future CLI, HTTP/API,
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

## Key Decisions

### 1. Build Reconciliation Before Tax, With Accounting In Parallel

The first major milestone after fact-path alignment is deterministic
reconciliation, not ACB math. Minimal accounting projection should advance in
parallel on the same canonical facts.

Reason:

- `2023-08-05` is a transaction cutoff, not a balance-guaranteed checkpoint
- the best available checkpoint evidence is around `2026-03-23`
- tax computation is not trustworthy until the fact set lands on a confirmed
  checkpoint
- accounting and reconciliation validate different properties of the same fact
  set and should remain separate capabilities

### 2. Keep CoinTracking At The Edge

CoinTracking remains supported for:

- one concrete CSV output adapter
- historical regression through dev-only oracle tooling

CoinTracking must not remain the core ledger model, core schema vocabulary, or
required runtime input surface. Production code may render CoinTracking CSV,
but report readers, comparison tolerances, and oracle heuristics must stay
outside `src/tallylot/`.

### 3. Replace The Current Transaction Center With A Richer Fact Model

The current normalized transaction model is too narrow for:

- multi-leg transactions
- collateral, loan, and liquidity flows
- correction and supersession chains
- valuation provenance
- independent journaling
- jurisdiction-neutral tax policy

The repo should introduce a new provider-neutral fact model and replace the
current normalized transaction model directly. Do not add compatibility
wrappers, parallel legacy names, or dual-write shims just to preserve the old
shape.

### 4. Use Layered Classification

A single `category` string is not a stable center for the next phase.

Every transaction fact should support distinct classification layers:

- `EconomicKind`: provider-neutral semantics
- `ProjectionHint`: output projection metadata for external renderers
- `TaxTreatmentHint`: jurisdiction-neutral tax intent
- `AccountingIntentHint`: accounting intent

### 5. Keep The Core Runtime Asset-Class Agnostic

The internal runtime should generalize across financial asset classes even when
the current adapters and policies are crypto-first.

Rules:

- core facts, checkpoints, accounting, and tax seams should avoid
  crypto-exclusive semantics unless the concept is truly crypto-specific
- crypto, FX, securities, and later import or output surfaces should enter
  through adapters and policy contracts rather than through domain renames or
  special-case compatibility shims
- repo, package, and CLI naming may remain stable for now; internal abstractions
  should still be chosen so later generalization does not require another core
  rewrite

### 6. Keep The Ledger Replaceable

Use Ledger CLI first because it is permissive, mature, and scriptable, but keep
all journaling behind a renderer port so later Beancount or hledger adapters do
not require domain refactors.

### 7. Keep The Tax Layer Replaceable

Implement Canadian capital-account handling first, but keep policy behind a tax
policy port so future jurisdictions do not require a domain rewrite.

### 8. Expand `pydantic` At Boundaries, Not In The Core Domain

Use `pydantic` for:

- config
- external artifact parsing
- CoinTracking report row models
- CLI or API request validation
- adapter manifest validation

Keep domain models as frozen dataclasses, enums, and value objects so business
rules remain explicit and tool-friendly.

### 9. Keep On-Chain Identity Canonical And Output Labels Separate

On-chain runtime location identity must be identifier-rooted and chain- or
network-scoped rather than source-label-derived.

Rules:

- EVM-family owned locations use `evm:<network>:<address>`.
- Non-EVM on-chain locations use their chain namespace such as
  `near:<account>`, `bitcoin:<address>`, `tron:<address>`, or
  `solana:<address>`.
- Derived on-chain sublocations append a stable suffix such as
  `near:<account>:staking`.
- Friendly source labels, wallet names, and renderer-facing labels stay in
  `source`, `location_label`, annotations, and output-adapter display logic.
- Output adapters such as CoinTracking may render the source label for
  on-chain facts, but they must not rewrite or own the canonical `location_id`.

### 10. Route Source Families By Content And Block Mixed Captures

Source-family ownership must be established by adapter-declared schema or
content signatures before filename hints.

Rules:

- profiling records recognized file-family claims per file
- translation should consume those family claims instead of rediscovering
  provider filenames
- path or filename hints are low-confidence tie-breakers only
- if one raw source directory mixes incompatible adapter families, profiling
  emits a blocking scan issue and normalization must refuse the capture
- if a translation-capable adapter recognizes a supported family but emits no
  facts and no explicit issues or reviews, normalization emits
  `no_supported_activity` instead of silently succeeding

## Target Architecture

Core abstractions added from this point forward must stay neutral enough to
support multiple asset classes. If a term is only correct for one provider,
chain, or asset class, keep it adapter-local unless the domain concept itself
is inherently specific.

### Domain Packages

- `domain/transactions/`
  - transaction facts, legs, valuations, ids, corrections, projection enums
- `domain/reconciliation/`
  - balance assertions, transfer links, checkpoint continuity, materiality rules
- `domain/accounting/`
  - journal entries, postings, balance checks, journal intents
- `domain/tax/`
  - tax records, pool state, policy contracts, unsupported tax items

### Application Capabilities

- `application/intake/`
  - manifest generation plus intake planning and apply workflows
- `application/profiling/`
  - source profile construction, inventory inspection, and timezone review
- `application/normalization/`
  - orchestrate source translation into fact artifacts and source-backed
    evidence
- `application/reconciliation/`
  - reserve for transfer linking, checkpoint continuity, and fact-level drift
    detection
- `application/checkpoints/`
  - build source-backed checkpoint evidence and checkpoint-supporting wallet
    aggregates
- `application/accounting/`
  - journal assembly, ledger validation, and accounting summaries
- `application/tax/`
  - policy application, ACB updates, and disposition or income outputs
- `application/outputs/`
  - render external artifacts from facts, journals, or tax results

### Interfaces

- `interfaces/cli/`
  - current operator-facing entry points over application capabilities
- `interfaces/api/`
  - reserve for a future thin HTTP or agent-facing surface over the same typed
    application workflows

Rules:

- CLI, API, and agent entrypoints should share use-case contracts instead of
  growing separate orchestration logic.
- Application request and response DTOs should trend toward transport-safe
  resource references so a future API does not inherit raw filesystem `Path`
  assumptions as its public contract.
- Long-running workflows should expose explicit job or artifact references at
  the interface boundary rather than relying on shell-owned temporary paths.

### Ports

- typed source translation contracts under `ports/source_translation.py`
- typed fact and evidence repositories under `ports/facts.py` and
  `ports/evidence.py`
- typed adapter contracts under `ports/source_adapters.py`,
  `ports/output_adapters.py`, and `ports/adapter_contracts.py`
- future journal, checkpoint, and tax ports by capability instead of generic
  catch-all storage contracts

### Adapter Responsibilities

- source adapters translate raw exports into the shared adapter draft model and
  surface explicit issues or reviews
- output adapters render facts into CoinTracking, Ledger CLI, and report
  artifacts
- source adapters return `SourceTranslationBatch`; they do not emit output
  rows, checkpoint decisions, or tax policy decisions directly
- CoinTracking-specific column defaults, `Tx-ID` behavior, and row-shape
  metadata stay inside the CoinTracking output adapter package rather than in
  provider-local source code
- CoinTracking rendering must validate that a fact stays within the adapter's
  published render policy rather than truncating richer legs silently
- adapters do not own tax logic, checkpoint policy, or reconciliation rules
- adapters should stay focused on source/output translation. Core data
  manipulation, verification, and workflow policy belong in application and
  domain code.
- application services own derived-balance assembly. Adapters return balance
  evidence only when the source actually provides it.
- normalization owns production statement-backed balance evidence for supported
  providers. Adapters may publish canonical quantity evidence through
  `SourceTranslationBatch.balance_evidence`, but market-value totals and other
  valuation-only rows are not canonical balance assertions.
- adapters may declare numeric precision expectations for source fields when
  decimal scale is part of the source contract. Shared adapter support should
  validate displayed raw-text fractional digits and support exact or minimum
  scale checks so rounded export values are surfaced explicitly rather than
  normalized silently.

## Input And Oracle Boundaries

The platform-agnostic core must distinguish between operational inputs and
optional support artifacts.

### Normal Runtime Inputs

These are valid operational inputs for reconstruction, reconciliation, and tax
computation:

- source-platform exports
- wallet and explorer exports
- statements and balance evidence
- deterministic checkpoint packages intentionally created by this system
- opening-state imports intentionally adopted as checkpoints

### Optional External Input Formats

These may be supported through adapters, but the system must not require them
for normal operation:

- CoinTracking trade-table style imports
- CoinTracking CSV import/export shapes
- other portfolio-tracker import formats added later through adapters

### Oracle-Only Support Artifacts

These are comparison inputs only:

- CoinTracking `Roll Forward in CAD`
- CoinTracking `Realized Gain or Loss in CAD`
- CoinTracking `Average Purchase Price`
- CoinTracking `Double-entry`
- historical CoinTracking tax reports

Do not wire business logic so these artifacts are required to reconstruct facts,
balances, journal entries, or tax state. Keep oracle code outside
`src/tallylot/`, preferably under `tools/oracles/`.

### Boundary Rule

If every CoinTracking tax report disappeared, the system should still be able
to:

- normalize source evidence
- build checkpoints
- reconcile balances
- compute tax state
- render journal output

The only lost capability should be comparison against the external oracle.

## Schema Contract

### Repo-Wide Temporal Precision Contract

- Use one timing convention everywhere in the repo:
  - exact-time fields use UTC-aware `*_at` values
  - fields that may be date-only or exact-time use `*_at` plus
    `*_precision`
- `*_precision` uses one shared enum with at least:
  - `timestamp`
  - `date`
- Date-only values are stored distinctly from exact timestamps even when an
  exact timestamp falls at midnight.
- Adapters are responsible for preserving this distinction at translation time.
- Infer precision from the source contract and parsed field shape, not from the
  normalized clock value. An exact midnight timestamp remains `timestamp`
  precision; a date-only source value remains `date` precision.
- New domain and port fields must adopt this convention instead of introducing
  provider-local date flags, boolean precision markers, or mixed string shapes.

### Current Fact-Shape Contract

- `TransactionFact` and `EconomicActivityDraft` use one canonical `legs` tuple.
- Fact construction requires successful identifier resolution to exactly one
  `InstrumentId`. Unresolved or ambiguous identity must emit review output and a
  blocking issue rather than guessing.
- Every leg carries:
  - stable `leg_id`
  - signed `quantity`
  - semantic `LegKind`
  - optional adapter-detail `subtype`
  - optional `attributed_to_leg_id` metadata
- signed quantities use one meaning everywhere:
  - positive increases the balance of the leg location
  - negative decreases the balance of the leg location
- `attributed_to_leg_id` is valid only on non-`primary` legs and only when
  it references one concrete leg in the same fact.
- `FactLegPolicy` is generic and per-kind:
  - `LegShapeLimit` declares `min_count`, `max_count`, `min_positive_count`,
    `max_positive_count`, `min_negative_count`, and `max_negative_count`
  - no duplicate kinds
  - minimum counts cannot exceed maximum counts
  - signed-count limits cannot exceed per-kind totals
  - unspecified kinds are disallowed
  - zero-`primary` shapes are opt-in through the declared policy
- Current shared policy constants cover:
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

### Current Normalization Window Contract

- Runtime timestamps are timezone-aware UTC in drafts, facts, balances, and
  balance evidence. Persisted artifact timestamp text remains
  `YYYY-MM-DD HH:MM:SS` and is interpreted as UTC on read.
- Fields that may be date-only or exact-time persist both `*_at` and
  `*_precision` so exact midnight timestamps remain distinguishable from
  date-only values.
- `facts.csv` is schema-versioned and readers fail fast on unexpected
  `schema_version` values; rebuilding from raw evidence is the supported
  recovery path after fact-shape breaks.
- `balances.csv` and `balance_evidence.csv` persist canonical `instrument_id`
  values and use `as_of_at` plus `as_of_precision` rather than bare symbol or
  timestamp columns.
- cross-source balance corroboration is additive in the first release. It
  consumes normalized `balances.csv` plus `location_inventory.csv`, writes
  sidecar corroboration artifacts, and does not redefine the primary
  source-local clean-date gate yet.
- Windowed normalization applies to:
  - `facts.csv`
  - `fact_annotations.json`
  - `balances.csv`
  - `exceptions.csv`
  - `normalization_reviews.csv`
- Windowed normalization does not apply to:
  - `balance_evidence.csv`
  - `location_inventory.csv`
- source-scope portfolio evidence that does not itself prove wallet ownership,
  such as MetaMask portfolio CSV rows, may contribute balance evidence only for
  same-source same-chain rows and must remain explicitly caveated as
  source-folder-scoped rather than globally authoritative identity proof.
- Review records carry `context_timestamp`, dataset-level untimed reviews stay
  visible when a window is active, and summaries report
  `reviews_outside_normalization_window`.

### Transitional Adapter Draft Seam

Source normalization should translate through `EconomicActivityDraft` until all
adapters emit `TransactionFact` artifacts directly.

Required draft responsibilities:

- stable identity claims plus evidence references
- UTC-aware timestamp and provenance
- optional `effective_at`
- optional `effective_precision`
- account and wallet scope
- one canonical `legs` tuple only; no separate fee lane
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
- shared support stays adapter-agnostic and registry-driven; adapters publish
  manifests, translation registries, and provider-local coverage metadata
- one shared fact builder owns draft-to-fact conversion
- draft-only provenance references and review markers must survive compilation
  through a fact-keyed sidecar artifact instead of being dropped
- one shared projection mapper owns the mapping from layered classifications
  into concrete output-adapter row types
- one shared projection mapper owns CoinTracking CSV row construction
- grouped operations and provider-local export families must resolve through
  explicit translation registries, not ad hoc adapter entry-point branching

### Core Fact Model

Add `TransactionFact` as the new system-of-record object.

Required fields:

- identity
  - internal id
  - source id
  - adapter id
  - external ids
  - tx hash
- time
  - event timestamp
  - optional `effective_at`
  - optional `effective_precision`
  - timestamp provenance
  - timestamp precision
- participants
  - account
  - wallet
  - optional counterparty hints
  - ownership scope
- economics
  - `tuple[EconomicLeg, ...]`
  - legs use canonical `InstrumentId`
  - legs carry stable `leg_id`
  - legs use signed `quantity: Decimal`
  - explicit per-kind leg-shape policy
  - optional grouped correction or bundle links
  - beneficial ownership change classification
- valuation
  - `tuple[Valuation, ...]`
  - currency, amount, method, provenance, confidence
- projection and policy hints
  - optional `ProjectionHint`
  - optional `TaxTreatmentHint`
  - optional `AccountingIntentHint`
- annotations
  - fact-keyed provenance and review-marker sidecar for draft-only metadata
- status
  - unsupported flag
  - ambiguity flag
  - review-required flag

### Supporting Types

- `EconomicLeg`
- `InstrumentIdentityClaim`
- `EffectiveTime`
- `TemporalPrecision`
- `Valuation`
- `TransferLink`
- `BalanceAssertion`
- `CorrectionRecord`
- `CheckpointAssertion`
- `JournalEntryModel`
- `Posting`
- `TaxComputationRecord`
- `UnsupportedTaxItem`

### Required Enums

Lock these early:

- `EconomicKind`
- `LegKind`
- `OwnershipChange`
- `ValuationMethod`
- `CorrectionReason`
- `ProjectionHint`
- `TaxTreatmentHint`
- `AccountingIntentHint`

## Current CoinTracking Adapter Contract

### Full Type Surface

Lock the current CoinTracking output taxonomy now so the projection metadata
used by that adapter does not churn later.

Trade types:

- `Trade`
- `Margin Trade`
- `Derivatives / Futures Trade`

Incoming types:

- `Deposit`
- `Income`
- `Gift / Tip`
- `Reward / Bonus`
- `Mining`
- `Airdrop`
- `Staking`
- `Masternode`
- `Minting`
- `Mining (commercial)`
- `Dividends Income`
- `Lending Income`
- `Interest Income`
- `Derivatives / Futures Profit`
- `Margin Profit`
- `LP Rewards`
- `Airdrop (non taxable)`
- `Receive Loan`
- `Remove Collateral`
- `Remove Liquidity`
- `Receive LP Token`
- `Other Income`
- `Income (non taxable)`

Outgoing types:

- `Withdrawal`
- `Spend`
- `Donation`
- `Gift`
- `Stolen`
- `Lost`
- `Borrowing Fee`
- `Settlement Fee`
- `Margin Loss`
- `Margin Fee`
- `Derivatives / Futures Loss`
- `Provide Liquidity`
- `Return LP Token`
- `Other Fee`
- `Other Expense`
- `Expense (non taxable)`
- `Add Collateral`
- `Repay Loan`
- `Liquidation`

### Oracle And Projection Notes

- normalize label aliases such as `Gift / Tip` and `Gift/Tip`
- treat Double-entry report labels such as `Deposit (IN)` as report-only labels,
  not core transaction labels
- preserve optional CoinTracking valuation and `Tx-ID` fields inside
  CoinTracking-only projection adapters

### Oracle Inputs To Support

Add dedicated readers for:

- `Trade Table`
- `Trade List`
- `Double-entry`
- `Roll Forward in CAD`
- `Realized Gain or Loss in CAD`
- `Average Purchase Price`

Use these for comparison and regression only. Do not normalize them into the
same source-fact path as exchange and wallet exports.

Keep them in dev-only tooling under `tools/oracles/` so production state does
not depend on their presence.

## Delivery Sequence

### Phase 0. Design Lock And Migration Plan

Estimated effort: `8` to `12` hours

Deliverables:

- final schema and package decisions
- roadmap updates
- migration plan from normalized transactions to transaction facts
- provenance policy for external ideas and direct code reuse

### Phase 1. Boundary Models And Dev-Only Oracle Readers

Estimated effort: `14` to `22` hours

Deliverables:

- Pydantic row models for CoinTracking report families
- parser services for all oracle exports under `tools/oracles/`
- projection-type enum and alias normalization for current output adapters
- comparison-ready artifact contracts

### Phase 2. Core Fact Model And Direct Normalization Replacement

Estimated effort: `18` to `28` hours

Deliverables:

- transaction fact domain package
- normalization result evolution to emit fact artifacts directly
- downstream service updates to consume fact artifacts without wrappers
- parity tests for current adapters

### Phase 3. Deterministic Reconciliation And Checkpointing

Estimated effort: `18` to `28` hours

Deliverables:

- exact balance assertion artifacts comparing derived snapshots to source-backed
  evidence
- transfer linking
- balance assertions
- checkpoint builder around `2026-03-23`
- continuity reports
- deterministic correction handling for events such as the GALA redistribution

### Phase 4. Accounting Layer And Ledger CLI Hard Gate

Estimated effort: `14` to `22` hours

Deliverables:

- internal journal model
- Ledger CLI renderer
- journal validation results
- accounting summaries tied to checkpoint and reconciliation outputs

### Phase 5. Canadian Tax MVP

Estimated effort: `24` to `36` hours

Deliverables:

- Canadian pooled ACB engine
- disposition and income outputs
- unsupported-item and ambiguity reporting
- carry-forward and year summary outputs for `2023`, `2024`, and `2025`

### Phase 6. Filing Workflow And Closeout

Estimated effort: `10` to `16` hours

Deliverables:

- filing-ready workflow
- checkpoint continuity gate
- CoinTracking oracle comparison for tax outputs
- roadmap capture for deferred cases

### Phase 7. Open-Source Hardening

Estimated effort: `20` to `32` hours

Deliverables:

- sanitized fixtures
- clearer licensing and provenance docs
- public-facing scope description
- generalized docs for non-personal use

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

Unsupported or ambiguous facts must produce explicit outputs and roadmap items.
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
- exact balance assertion workflow over `balances.csv` and
  `balance_evidence.csv`
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
  would otherwise be added; do not let facts, checkpoints, or tax policy land
  in new flat prefix piles
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
