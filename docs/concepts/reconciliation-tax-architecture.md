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
parallel on the same shared facts.

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

These layered fields are the current fact-bridge contract, not a rule that
every earlier stage must guess final policy meaning. When a provider row
cannot safely support one final economic, accounting, or tax reading, the
target `ClaimBundle` should preserve that ambiguity until one safe canonical
economic fact or later stage-owned policy decision is available.

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
- manual balance submission row models
- CoinTracking report row models
- CLI or API request validation
- adapter manifest validation

Keep domain models as frozen dataclasses, enums, and value objects so business
rules remain explicit and tool-friendly.

### 9. Keep On-Chain Identity Identifier-Rooted And Output Labels Separate

On-chain runtime location identity must be identifier-rooted and chain- or
network-scoped rather than source-label-derived.

Rules:

- EVM-family owned locations use `evm:<network>:<address>`.
- Native EVM-family assets use `asset:evm:<network>:native`.
- Native NEAR assets use `asset:near:native`.
- In-scope public-ledger adapters must emit native asset ids with immutable
  chain identity directly; symbol-only public-ledger asset ids remain
  unsupported for provider hydration until immutable asset identity is proven.
- Non-EVM on-chain locations use their chain namespace such as
  `near:<account>`, `bitcoin:<address>`, `tron:<address>`, or
  `solana:<address>`.
- Derived on-chain sublocations append a stable suffix such as
  `near:<account>:staking`.
- Friendly source labels, wallet names, and renderer-facing labels stay in
  `source`, `location_label`, annotations, and output-adapter display logic.
- Output adapters such as CoinTracking may render the source label for
  on-chain facts, but they must not rewrite or own the runtime `location_id`.

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

### 11. Keep Capture Identity In Metadata, Not In Paths

One intake run is one capture, regardless of how many statement months or
export periods it contains.

Rules:

- use a stable `capture_uid` as the capture identity
- use a human-readable `capture_label` only for the raw folder name
- treat inferred periods and any inferred `capture_id` heuristics as metadata,
  not as the routing key, grouping identity, or capture ownership model
- keep all untouched upstream originals for the capture under one raw capture
  root instead of repartitioning them into inferred month or year folders
- use explicit capture registry records instead of overloading one source row
  with a single `capture_path`

### 12. Separate Capture Normalization From Source Assembly

Normalization remains capture-scoped. Reconciliation becomes source-assembly
scoped.

Rules:

- `source profile` and `source normalize` operate on exactly one materialized
  raw capture root
- both commands must fail explicitly when the input is not a valid
  `evidence/raw/source/<source>/<capture_label>/` root with matching
  `capture.json` metadata
- capture-normalized outputs live under a capture-owned root
- `source assemble` is the only supported bridge from accepted captures to the
  reconciliation-ready source dataset
- reconciliation reads only assembled source datasets, never raw capture trees
  or ad hoc multi-capture crawls
- duplicate, overlap-review, and superseded captures stay explicit in the
  capture registry and are excluded from source assembly unless accepted

### 13. Use One Shared Statement Extraction Capability

Statement-backed evidence must not fork into separate normalization and
checkpoint parsers.

Rules:

- add one shared application seam for statement extraction
- let adapters contribute statement matching, parsing, and instrument-claim
  resolution hooks through bounded plugin methods
- use that shared service both when normalization emits source-backed balance
  evidence and when `checkpoint extract-pdf-balances` is invoked directly
- let the shared service own capture-inventory-backed document discovery,
  ambiguity rules, typed provenance locator construction, and shared issue or
  review handling rather than duplicating that orchestration in providers

### 14. Keep Typed Provenance In Runtime Models

Artifact rows need flattened provenance columns, but runtime models should keep
one typed locator seam until the storage boundary.

Rules:

- keep capture-scoped provenance as a typed runtime concept
- flatten provenance only in codecs and artifact writers
- reuse one flattened locator family across balance evidence, issue rows,
  review rows, and location inventory evidence rows
- keep row or page anchors separate from file location rather than collapsing
  them into one ad hoc string

### 15. Make Source Assembly Deterministic And Rerun-Safe

Source assembly owns one generated output surface per source and should rewrite
that surface deterministically on rerun.

Rules:

- `source assemble` rewrites only its known generated artifacts under
  `working/normalized/sources/<source>/`
- reruns must remove stale generated files that no longer have source data
- assembly lifecycle and source summary state must be derived by reducers from
  capture registry state, not by ad hoc latest-write behavior

### 16. Treat Semantic Workspace Validation As A First-Class Repo Capability

The supported validation path is raw-evidence derivation, not migration
wrappers.

Rules:

- validate semantic parity by deriving typed artifacts from raw evidence into
  an initialized workspace
- compare semantic parity, not path identity
- ignore expected `capture_uid` and `capture_label` differences when two
  workspaces are otherwise semantically identical
- compare the semantic registry surface, raw completeness, assembled source
  metrics, and reconciliation status counts
- allow expected-difference fixtures only for declared issue-count or
  review-count drift with an explicit reason
- keep semantic parity validation in repo-native tooling under `tools/`
- do not add one-off migration utilities or compatibility wrappers just to
  preserve a superseded capture layout

### 17. Keep Manual Balance Submission Checkpoint-Owned And Boundary-Validated

Manual balance submission is a supported operational path for producing
`balance_snapshots.csv` and `balance_references.csv`, but it is not an
adapter-owned schema.

Rules:

- the user-facing package under
  `working/supporting_artifacts/balance_submissions/<source>/` is a
  checkpoint-owned pre-reconciliation input surface
- `checkpoint scaffold-balance-submission` and `checkpoint submit-balances`
  own that validation and materialization path inside
  `application/checkpoints/`
- the shared reconciliation schema still lives under the chosen output root,
  normally `working/normalized/sources/<source>/`
- `balance_snapshots.csv` and `balance_references.csv` are the only runtime
  balance inputs; `balances.csv` and `balance_evidence.csv` are superseded
  generated outputs and are not read at runtime, and no compatibility wrappers
  or dual-read logic should keep them alive
- manual submission records `operator_assertion` runtime references and must
  not fabricate or widen source-backed `source_document` references
- runtime reconciliation resolves references through one unified
  `balance_references.csv` artifact with precedence
  `source_document`, `network_api`, then `operator_assertion`
- filing-ready checkpoint status still requires source-backed or otherwise
  acceptable first-party references under the shared model
- optional submitted `location_inventory.csv` improves cross-source
  corroboration, but omitting it does not block source-local balance checks
- manual submission must preserve explicit user-provided `instrument_id`
  values and derive `location_id` values through shared runtime helpers rather
  than hand-authored location identifiers
- checkpoint submission row models stay validated at the boundary with
  `pydantic` so malformed or unsupported rows fail with explicit issues

### 18. Plan Translation Inputs In Core Before Adapter Translation

Capture-scoped normalization must decide which raw source files are translated
before adapter row translation runs.

Rules:

- adapters describe every valid translation input candidate for the capture,
  including coverage, freshness, grouping, replaceability, and comparability
  metadata
- the core planner in `application/normalization/` selects the deterministic
  candidate plan and records selected, superseded, and blocked outcomes before
  translation begins
- event-time coverage outranks path order, filename order, and discovery order
- ambiguous overlap, incomparable candidates, unknown coverage, or unresolved
  freshness ties are blocking normalization concerns, not adapter-local
  heuristics
- planner artifacts must preserve raw-input provenance explicitly through
  candidate and decision outputs rather than hiding file selection inside
  adapter code
- migrated adapters translate only the selected plan; legacy adapters may stay
  on the fallback `translate(...)` path until their candidate semantics are
  modeled accurately
- Coinbase is the first migrated adapter and future migrations should proceed
  in stages from path-order or filename-order adapters toward richer grouped
  multi-file inputs

## Target Architecture

Core abstractions added from this point forward must stay neutral enough to
support multiple asset classes. If a term is only correct for one provider,
chain, or asset class, keep it adapter-local unless the domain concept itself
is inherently specific.

### Canonical Pipeline Products

The target runtime should converge on one canonical flow:

`general intake -> surface reconciliation -> checkpoint adoption ->
journal expansion -> tax expansion`

Each stage narrows truth and then expands the next decision surface. Upstream
stages preserve optionality. Downstream stages force specificity. No stage may
guess a later-stage answer or suppress uncertainty that a later stage must
still see.

The canonical runtime products are:

1. `EvidenceBundle`
2. `ClaimBundle`
3. `EconomicDataset`
4. `ReconciliationDataset`
5. `CheckpointPackage`
6. `JournalDataset`
7. `TaxDeterminantDataset`
8. `TaxOutputDataset`

Current runtime note:

- today's `EconomicActivityDraft`, `TransactionFact`,
  `balance_snapshots.csv`, and `balance_references.csv` remain the active
  runtime center until the richer products land
- treat those contracts as the current bridge into the target pipeline, not as
  proof that the final architecture should stop at facts plus balances

### Stage Contracts

#### `EvidenceBundle`

`EvidenceBundle` is the deterministic intake product.

It should contain:

- selected raw source artifacts
- parsed boundary observations that remain source-local
- capture and source assembly provenance
- document, statement, and inventory observations
- deterministic selection decisions and superseded or blocked alternatives

It must promise:

- deterministic evidence selection
- stable provenance and locator references
- no forced economic meaning
- no forced tax, accounting, or reconciliation policy

It may block only when:

- source selection is nondeterministic
- parsing cannot produce stable source-local observations
- provenance is too unresolved to support later review

#### `ClaimBundle`

`ClaimBundle` is the source-local meaning layer.

It should contain claims such as:

- activity claims
- balance observation claims
- ownership and control claims
- location claims
- instrument identity claims
- contract term claims
- valuation claims
- explicit issues and reviews

It must promise:

- source-local semantics only
- preserved ambiguity when the source does not support one final reading
- provenance for every emitted claim
- candidate interpretations when one safe final meaning is not yet available

Rules:

- adapters may continue populating layered classifications on the current
  runtime path when they are safe and deterministic
- the target claim layer must allow unresolved economic, accounting, or tax
  classification when forcing those fields would guess
- `ClaimBundle` must be able to express materially unclassified rows instead of
  coercing everything into one `EconomicKind`

#### `EconomicDataset`

`EconomicDataset` is the first canonical narrowing.

It should contain only what the system can safely say happened economically.

It must preserve enough determinants for later reconciliation, accounting, and
tax work:

- signed legs
- instrument identity
- contract instance identity when applicable
- location identity
- legal owner, beneficial owner, and counterparty identity when known
- effective time and temporal precision
- settlement and supersession links
- optional valuation attachments with purpose and provenance
- provenance, confidence, and ambiguity markers

It must be able to express economically important surfaces beyond simple spot
flows:

- holdings movements
- cash movements
- obligations and rights
- settlements
- collateral state changes
- financing flows
- fees, rebates, and withholding
- corrections and supersession chains
- corporate actions and similar non-trade lifecycle events

It may block only when:

- a canonical fact would be false
- identity is too unresolved to emit a stable canonical fact
- the source collapses multiple materially different interpretations and the
  ambiguity is not representable safely

#### `ReconciliationDataset`

`ReconciliationDataset` is the surface-reconciliation product.

It should contain:

- transfer and linkage decisions
- balance targets, assertions, and continuity windows
- missing funding or settlement legs
- unresolved ownership transitions
- cross-source corroboration sidecars
- checkpoint candidates
- reconciliation-owned issues, gaps, and readiness state

It must promise:

- explicit completeness and continuity decisions
- explicit missing-leg and missing-evidence surfaces
- partial truth preservation when full clean-state is not yet available
- no rewriting of upstream economic truth to make a check pass

Rules:

- transfer linking belongs here, not in adapter translation
- checkpoint continuity belongs here before checkpoint adoption is accepted
- reconciliation may declare a subject or window unresolved, but it must not
  erase a valid partial balance or partial economic fact

#### `CheckpointPackage`

`CheckpointPackage` is the formal handoff between reconstruction and later
stateful work.

It should contain:

- accepted checkpoint assertions
- adopted opening state when intentionally imported
- supporting evidence and provenance
- continuity decisions into the accepted checkpoint
- explicit trust level and acceptance basis

Rules:

- keep checkpoint state as a first-class package boundary, not just a flag on
  reconciliation output
- source-backed evidence remains the preferred basis
- operator assertions may support runtime reconciliation but do not satisfy the
  filing-ready checkpoint requirement by themselves

#### `JournalDataset`

`JournalDataset` is the accounting expansion product.

It should contain:

- journal entries and postings
- posting provenance back to reconciled economics
- validation results
- unsupported accounting coverage gaps

It must promise:

- deterministic posting expansion from accepted upstream truth
- explicit balanced-versus-unbalanced validation
- explicit unsupported accounting gaps

Rules:

- accounting is a validator and renderer, not a truth-repair stage
- journal failures should surface upstream fact or reconciliation gaps instead
  of inventing local repairs

#### `TaxDeterminantDataset`

`TaxDeterminantDataset` is the policy-ready tax input surface.

It should contain:

- acquisitions
- dispositions
- income events
- financing costs
- internal transfers
- corporate actions
- valuations required for tax computation
- unresolved tax-owned gaps

It must promise:

- jurisdiction-neutral tax determinants, not final jurisdiction output
- explicit basis-affecting state changes
- explicit unresolved tax-specific blockers when reconciliation truth is
  sufficient operationally but not yet sufficient for tax

Rules:

- tax operates on reconciled economics plus accepted checkpoint truth
- journal output may corroborate tax readiness, but tax must not depend on a
  journal renderer succeeding unless the missing accounting information exposes
  a real upstream determinant gap
- tax must never invent missing economics

#### `TaxOutputDataset`

`TaxOutputDataset` is the jurisdiction-specific result surface.

It should contain:

- jurisdiction summaries
- schedules and forms
- carry-forward state
- explicit unsupported or deferred outputs

### Shared Sidecars

Every canonical product should reuse the same sidecar families.

#### Provenance

- one typed runtime provenance model
- flatten only at storage or export boundaries
- keep evidence locators and row or page anchors distinct

#### Gaps

Use one cross-stage gap contract rather than stage-local ad hoc issue shapes.

Every gap record should declare at least:

- `gap_id`
- `owner_stage`
- `blocking_for_stage`
- `subject_ref`
- `gap_kind`
- `known_facts`
- `missing_determinants`
- `candidate_interpretations`
- `required_evidence`
- `allowed_resolution_methods`
- `recommended_next_action`
- `confidence`
- `materiality`
- `provenance_refs`

`gap_kind` should stay explicit and closed over a controlled taxonomy such as:

- missing_evidence
- unresolved_identity
- unresolved_linkage
- contradiction
- policy_required_determination
- operator_override_required

#### Readiness

Use one readiness vocabulary across the pipeline:

- `semantic_ready`
- `reconciliation_ready`
- `checkpoint_ready`
- `accounting_ready`
- `tax_ready`

Rules:

- readiness must be sliceable by subject and time window, not just summarized
  once per whole dataset
- support at least source, location, instrument, position or contract,
  continuity segment, and checkpoint date slices
- dataset-level readiness is a reducer output over subject-level readiness, not
  the primary stored truth

#### Checkpoints

- one checkpoint assertion vocabulary
- one accepted checkpoint package surface
- one trust-level model that distinguishes source-backed, network-backed, and
  operator-backed support

### MVP Delivery Guardrails

The MVP should be intentionally narrow without painting the system into a
corner.

Rules:

- keep the current fact-plus-balances bridge as the active delivery path until a
  richer stage contract is needed by the next concrete slice
- land new stage products only when they unlock a real filing-critical or
  architecture-blocking behavior
- prefer one bounded reducer, compiler, or dataset contract per stage over
  building a general framework for every future variation up front
- do not build a full contract-lifecycle or multi-asset engine before an
  in-scope workflow needs that capability
- keep unsupported surfaces explicit through gaps instead of speculative partial
  implementations
- prioritize the filing-critical `2023` to `2025` reconstruction path even when
  choosing generic names and seams that can later generalize beyond crypto
- treat replaceable seams as typed ports and contracts, not as plugin systems
  that exist before a second concrete implementation needs them

### Generic Core Requirements

The shared core must stay broad enough for crypto, FX, securities, debt,
options, futures, staking derivatives, loans, funds, and later non-crypto
instruments without reshaping the engine.

The core should standardize concepts such as:

- `Instrument`
- `InstrumentTraits`
- `ContractInstance`
- `ContractTerms`
- `PositionState`
- `OwnershipScope`
- `Counterparty`
- `EconomicEvent`
- `EconomicLeg`
- `Observation`
- `Link`
- `CheckpointAssertion`
- `Valuation`
- `Posting`
- `TaxDeterminant`

The core must not assume the world is only:

- exchanges
- wallets
- chain transfers
- coin categories
- tracker-specific row types

### Identity Requirements

Cross-stage logic should keep identity layers explicit instead of overloading
one id field for several concerns.

The target pipeline should keep separate runtime seams for:

- instrument identity
- contract instance identity
- location identity
- legal owner identity
- beneficial owner identity
- counterparty identity

Location and instrument identity remain foundational runtime contracts. Later
reconciliation, checkpoint, accounting, and tax work should add the remaining
identity layers as first-class seams instead of collapsing them into
descriptions or adapter-local metadata.

### Domain Packages

- `domain/transactions/`
  - transaction facts, legs, valuations, ids, corrections, projection enums
- `domain/balances/`
  - balance targets, snapshots, references, assertions, and selection rules
- `domain/accounting/`
  - journal entries, postings, balance checks, journal intents
- `domain/tax/`
  - tax records, pool state, policy contracts, unsupported tax items

### Application Capabilities

- `application/intake/`
  - manifest generation plus capture-scoped intake planning and apply
    workflows
- `application/evidence/`
  - shared statement extraction, provenance locators, and document-family
    recognition
- `application/profiling/`
  - capture profile construction, inventory inspection, and timezone review
- `application/normalization/`
  - orchestrate one capture's translation-input planning, translation into fact
    artifacts, source-backed evidence, and fact-backed balance packages through
    `application/balances`
- `application/balances/`
  - target planning, snapshot derivation, reference resolution, exact-balance
    inspection and check workflows, cross-source corroboration, summary and
    blocker assembly, and deterministic merge policy
- `application/normalization/assembly/`
  - deterministic merge of accepted capture outputs into assembled
    source-scoped normalization datasets
- `application/reconciliation/`
  - reserve for transfer linking, checkpoint continuity, correction and
    supersession chains, and higher-order reconciliation beyond exact balance
    assertions over assembled source datasets
- `application/checkpoints/`
  - build source-backed checkpoint evidence, validate manual balance
    submission packages, and assemble checkpoint-supporting wallet aggregates
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
- planner-enabled source adapters describe translation input candidates and
  translate only the selected plan; they do not choose winning files
  independently once they opt into the planner contract
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
  references only when the source actually provides them.
- normalization owns production statement-backed `source_document` references
  for supported providers through the shared statement extraction seam.
  Adapters may publish quantity evidence through
  `SourceTranslationBatch.balance_references`, but market-value totals and
  other valuation-only rows are not balance assertions.
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

- `TransactionFact` and `EconomicActivityDraft` use one shared `legs` tuple.
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

- Runtime timestamps are timezone-aware UTC in drafts, facts, balance
  snapshots, and balance references. Persisted artifact timestamp text remains
  `YYYY-MM-DD HH:MM:SS` and is interpreted as UTC on read.
- Fields that may be date-only or exact-time persist both `*_at` and
  `*_precision` so exact midnight timestamps remain distinguishable from
  date-only values.
- `facts.csv` is schema-versioned and readers fail fast on unexpected
  `schema_version` values; re-deriving artifacts from raw evidence is the
  supported recovery path after fact-shape breaks.
- `balance_snapshots.csv` and `balance_references.csv` persist `instrument_id`
  values and use `target_at` plus `target_precision`; balance references also
  persist `observed_at` plus `observed_precision`.
- cross-source balance corroboration is additive in the first release. It
  consumes normalized balance snapshots plus `location_inventory.csv`, writes
  sidecar corroboration artifacts, and does not redefine the primary
  source-local clean-date gate yet.
- Windowed normalization applies to:
  - `facts.csv`
  - `fact_annotations.json`
  - `balance_snapshots.csv`
  - `exceptions.csv`
  - `normalization_reviews.csv`
- Windowed normalization does not apply to:
  - `balance_references.csv`
  - `location_inventory.csv`
- source-scope portfolio evidence that does not itself prove wallet ownership,
  such as MetaMask portfolio CSV rows, may contribute balance evidence only for
  same-source same-chain rows and must remain explicitly caveated as
  source-folder-scoped rather than globally authoritative identity proof.
- Review records carry `context_timestamp`, dataset-level untimed reviews stay
  visible when a window is active, and summaries report
  `reviews_outside_normalization_window`.

### Capture And Assembly Contract

- raw capture roots use `evidence/raw/source/<source>/<capture_label>/`
- capture metadata stores the stable `capture_uid`, intake timestamps,
  manifest fingerprint, and workspace-relative refs
- untouched upstream originals stay under the raw capture root even when they
  are statements, HTML exports, ZIP archives, or required sidecars
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

### Transitional Adapter Draft Seam

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
  - legs use `InstrumentId`
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

- final schema, package, and stage-boundary decisions
- roadmap updates
- migration plan from the current fact bridge into the canonical pipeline
- shared provenance, gap, readiness, and checkpoint-vocabulary decisions
- provenance policy for external ideas and direct code reuse

### Phase 1. Evidence And Claim Foundations Plus Oracle Readers

Estimated effort: `14` to `22` hours

Deliverables:

- deterministic `EvidenceBundle` and `ClaimBundle` contracts for the next
  pipeline slice
- claim ambiguity rules and shared gap or readiness foundations
- Pydantic row models for CoinTracking report families
- parser services for all oracle exports under `tools/oracles/`
- projection-type enum and alias normalization for current output adapters
- comparison-ready artifact contracts

### Phase 2. Core Fact Model And Direct Normalization Replacement

Estimated effort: `18` to `28` hours

Deliverables:

- transaction fact domain package
- claim-to-economic compilation seam
- normalization result evolution to emit fact artifacts directly
- downstream service updates to consume fact artifacts without wrappers
- parity tests for current adapters

### Phase 3. Reconciliation Dataset And Checkpoint Packages

Estimated effort: `18` to `28` hours

Deliverables:

- exact balance assertion artifacts comparing derived snapshots to source-backed
  evidence
- transfer linking
- balance assertions
- reconciliation dataset with explicit readiness, link, and continuity outputs
- checkpoint builder around `2026-03-23`
- accepted checkpoint package and trust-basis contracts
- continuity reports
- deterministic correction handling for events such as the GALA redistribution

### Phase 4. Journal Dataset And Ledger CLI Hard Gate

Estimated effort: `14` to `22` hours

Deliverables:

- internal journal model
- Ledger CLI renderer
- journal validation results
- accounting coverage gaps
- accounting summaries tied to checkpoint and reconciliation outputs

### Phase 5. Tax Determinants And Canadian Tax MVP

Estimated effort: `24` to `36` hours

Deliverables:

- tax determinant dataset contracts
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
