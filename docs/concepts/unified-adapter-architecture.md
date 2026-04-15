---
title: "Unified Adapter Architecture"
summary: "First-principles design anchor for the future unified adapter manifest, facets, adapter products, and deterministic verification model."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 60
related:
  - ROADMAP.md
  - docs/status/adapter-delivery-plan.md
  - docs/guides/write-an-adapter.md
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/domain-ontology.md
  - docs/concepts/reconciliation-tax-architecture.md
  - docs/concepts/oracle-boundaries.md
  - docs/concepts/transaction-classification.md
---

Read this document before shaping adapter changes. Use it as the forward design
anchor for source, portfolio, and output adapter work, even while the current
repo still runs on the older bundled adapter contracts.

This document is intentionally explicit. It is meant to be scrutinized,
challenged, and used as a design reference during later migration work.

Detailed target stage contracts are owned by
[`docs/concepts/pipeline-stage-contracts.md`](pipeline-stage-contracts.md), and
target ontology rules are owned by
[`docs/concepts/domain-ontology.md`](domain-ontology.md). This page focuses on
adapter responsibilities, adapter handoffs, and adapter-local implications of
those target contracts.

## Objective

Design one future adapter architecture that:

- makes adapters easier to build and reason about
- removes avoidable behavior drift between adapters
- centralizes deterministic workflow logic in shared services
- keeps provider-local code focused on provider-local semantics
- supports source, portfolio-style, and output surfaces without forcing them
  through unrelated responsibilities
- scales to reconciliation, checkpoint, accounting, and tax work without
  re-centering on a tracker-specific model

The future design must not be shaped by the current repo layout beyond the
actual jobs the repo must accomplish.

## Why The Current Shape Is Not The End State

The current runtime already contains valuable components:

- shared draft compilation
- translation-input planning
- shared statement extraction
- shared output-policy validation
- shared evidence and provenance artifacts

However, the current adapter shape still has one central flaw:

- the source-side contract bundles too many unrelated jobs into one plugin
  surface

Today a source adapter may be expected to do all of the following:

- match a source during profiling
- classify file families
- match and route intake files
- validate timezone policy
- extract location inventory
- recognize and parse statement PDFs
- resolve statement instrument claims
- describe translation candidates
- translate selected inputs or fallback inputs

That bundling creates three problems:

1. Adapters do too much.
2. Capability flags do not fully narrow the actual implementation burden.
3. Workflow behavior can drift because shared orchestration concerns stay
   scattered across provider-local entry points.

The future architecture should unify the model without creating another giant
"do everything" interface.

## Core Design Decision

The future system should unify adapters around four things:

- one universal manifest model
- a small set of purpose-defined facets
- one shared adapter product pipeline
- one deterministic verifier model

It should not unify adapters around one monolithic method surface.

This means:

- portfolio is not a special third adapter species
- portfolio is a reader surface that emits balance, position, or statement
  claims instead of only activity claims
- output is not a source adapter with inverted arrows
- output is a writer surface that consumes runtime or projection data and emits
  target-specific artifacts

## First-Principles Basis

This design follows durable architecture ideas rather than repo-local
convenience.

### 1. Purpose-Defined Ports Beat Technology-Defined Layers

Ports should represent a meaningful job boundary, not a technology or folder
boundary.

Implication:

- "source adapter" is too broad if it means discovery, routing, parsing,
  planning, translation, statement extraction, and location extraction

### 2. Shared Intermediate Representations Reduce Drift

Complex ingestion and rendering systems stay simpler when adapters do not
translate directly from raw input to final output in one jump.

Implication:

- the system needs a stable sequence of intermediate products with explicit
  invariants and verification points

### 3. Determinism Must Be A Contract, Not A Hope

Any surface that depends on unordered iteration, filename order, path order, or
 hidden heuristics is not trustworthy enough for reconciliation and tax work.

Implication:

- stable ordering, fingerprints, replacement rules, and blocking ambiguity
  must be explicit

### 4. Provenance Is A First-Class Runtime Concern

Financial reconstruction requires trust in where each fact and balance
reference came from.

Implication:

- provenance must remain typed in runtime models and must not be reduced to an
  ad hoc string until artifact boundaries

### 5. Assertions And Annotations Must Stay Separate

Systems become fragile when structural facts, advisory notes, and review hints
share one loose payload.

Implication:

- hard assertions, soft annotations, blocking issues, and review records need
  distinct types and distinct rules

### 6. Schema Evolution Needs Stable Identity

Schema compatibility is simpler when every adapter product has versioned
identity and stable fingerprints.

Implication:

- manifests and adapter product schemas need explicit versioning and
  fingerprint rules

## Non-Goals

This architecture is not trying to:

- preserve the current bundled source contract under new names
- make every provider look identical at the semantic level
- turn adapters into giant declarative config files with no provider-local code
- hide unsupported behavior behind coercion or defaults
- keep compatibility wrappers alive indefinitely
- center the architecture on CoinTracking or any other tracker shape

## Design Goals

- Adapters should be thin at their entry points.
- Provider-local code should focus on provider-local evidence and semantics.
- Shared orchestration should live in the core planner, compiler, verifier, and
  artifact writers.
- Input, portfolio, and output surfaces should use one manifest family and one
  shared terminology.
- Every major handoff should have a deterministic fingerprint.
- Unsupported or ambiguous data should become explicit issues or reviews.
- Future migration should be incremental and family-based, not big-bang.

## Terminology

### Evidence

Untouched or boundary-parsed provider material such as CSV exports, workbook
tabs, PDFs, HTML reports, explorer exports, or future API payloads.

### Claim

A provider-local semantic assertion derived from evidence but not yet accepted
as bridge or downstream runtime data.

Examples:

- "this row describes a trade-like activity"
- "this statement row reports a quantity balance as of a date"
- "this wallet export proves ownership of this chain-scoped identifier"

### Runtime Data

Downstream-owned runtime products such as `EconomicFacts`,
`ReconciliationState`, `Checkpoint`, `Journal`, `TaxInputs`, and
`TaxOutputs`.

### Projection

A target-specific but still structured representation derived from semantic
data, such as a CoinTracking row model or a future journal posting set.

### Artifact

A serialized file, directory, or byte-oriented output written for operators,
tools, or external systems.

## Adapter Product Pipeline

The future adapter system should revolve around evidence, claims, explicit
bridge outputs while the migration remains active, and target-local rendering.

Boundary note:

- this document defines the adapter-scoped handoff products only
- `docs/concepts/reconciliation-tax-architecture.md` remains the core runtime
  architecture anchor for `EconomicFacts`, `ReconciliationState`,
  `Checkpoint`, `Journal`, `TaxInputs`, and
  `TaxOutputs`
- `docs/concepts/pipeline-stage-contracts.md` owns the shared target-product
  versioning, kernel-and-envelope, and downstream stage-contract rules that
  adapter products must align with
- adapter work should map into that runtime pipeline rather than creating a
  second competing core architecture

### 1. EvidenceSet

Purpose:

- represent the evidence selected for one adapter-owned read operation
- preserve discovery results, family classification, provenance, and typed
  parse outputs without making semantic commitments too early

Owned by:

- reader facets and shared evidence orchestration

Must include:

- adapter id
- capture or input identity
- manifest version and fingerprint
- evidence members with typed provenance
- evidence family ids
- parse diagnostics
- deterministic member ordering
- evidence fingerprint

Must not include:

- current bridge facts or downstream runtime products
- target-specific output rows

Typical contents:

- typed CSV rows
- workbook sheets
- PDF-extracted balance rows
- discovered document metadata
- recognized evidence families

### 2. ClaimSet

Purpose:

- hold provider-local semantic claims before shared compilation

Owned by:

- reader and translation facets

Claim types may include:

- `ActivityClaim`
- `BalanceObservationClaim`
- `OwnershipClaim`
- `LocationClaim`
- `StatementClaim`
- `InstrumentIdentityClaim`
- `ContractTermClaim`
- `ValuationClaim`
- `ProjectionAnnotation`
- `EvidenceIssue`
- `EvidenceReview`

Must include:

- deterministic claim ids
- typed provenance references back to the evidence set
- structural status for each claim
- blocking versus advisory distinction
- claim-set fingerprint

Must not include:

- inferred final identities that have not been resolved
- writer-specific rows

### 3. Bridge Result While The Current Path Remains Active

Purpose:

- describe the current bridge bundle honestly while adapter migration is still
  landing

Current truth:

- source adapters still return `SourceTranslationBatch`
- that bridge bundle currently carries drafts, balance references, balance
  reference issues, issues, reviews, and location inventory

Rules:

- this is a migration seam, not the future adapter architecture center
- do not describe this bundle as if it owns `EconomicFacts`
- adapter-side bundles must not overload "economic output" with
  balance snapshots, balance references, issues, reviews, and location
  inventory as if they shared one semantic meaning
- the main runtime architecture doc owns the meaning of downstream products

Target-direction naming note:

- future code may move toward the name `TranslationResult`
- current-state docs must continue using `SourceTranslationBatch` until code
  changes land

### 4. ProjectionBundle

Purpose:

- hold target-specific structured outputs before serialization

Owned by:

- writer facets and shared projection validation

Examples:

- CoinTracking CSV row models
- Ledger posting sets
- future tax package rows

Must include:

- target id
- target version
- source fingerprint
- projection fingerprint
- target constraint validation results

### 5. ArtifactBundle

Purpose:

- represent serialized outputs written to disk or another delivery boundary

Owned by:

- shared artifact writers plus writer facets

Examples:

- CSV files
- JSON plan files
- Markdown summaries
- future API payload packages

Must include:

- artifact paths or identifiers
- media type or artifact kind
- byte or row counts
- artifact fingerprint
- manifest and source fingerprint references

## Why These Products Matter

This pipeline gives the architecture explicit checkpoints:

- evidence can be verified independently of semantics
- claims can be verified independently of shared compilation
- bridge or runtime data can be verified independently of target projections
- target projections can be validated independently of final serialization

That separation is the main mechanism for reducing adapter drift.

## Adapter Model

The future adapter system should have one universal manifest and a small set of
optional facets.

### Universal Manifest

Every adapter should publish one `AdapterManifest`.

The manifest is the durable contract. Facets are executable behaviors attached
to that contract.

### Manifest Responsibilities

The manifest should answer:

- what evidence kinds this adapter can read or write
- what adapter or runtime products it can emit or consume
- what facets it implements
- which determinism guarantees it provides
- which schema versions it supports
- what constraints or unsupported surfaces it declares

### Manifest Shape

The exact field list may change, but the manifest should eventually cover at
least the following areas.

| Category | Representative fields | Purpose |
| --- | --- | --- |
| Identity | `adapter_id`, `display_name`, `version`, `family`, `status` | Stable adapter identity and support posture. |
| Direction | `implemented_facets`, `reads`, `writes` | Declares whether the adapter probes, reads, translates, writes, or combines those jobs. |
| Evidence | `accepted_evidence_kinds`, `recognized_family_ids`, `statement_kinds` | Declares what raw or parsed evidence the adapter understands. |
| Product flow | `emits_claim_types`, `emits_bridge_types`, `consumes_runtime_types`, `emits_projection_types` | Defines product flow explicitly. |
| Determinism | `ordering_contract`, `fingerprint_contract`, `planner_support`, `selection_modes` | Makes determinism a contract surface. |
| Identity | `supported_identifier_schemes`, `location_identity_rules`, `instrument_claim_rules` | Declares identity expectations. |
| Temporal and numeric policy | `timezone_policy`, `effective_time_policy`, `precision_policy` | Makes interpretation rules explicit. |
| Constraints | `unsupported_surfaces`, `hard_requirements`, `review_triggers` | Distinguishes unsupported from merely advisory. |
| Compatibility | `schema_version`, `compatibility_window`, `manifest_fingerprint` | Supports evolution and migration discipline. |

### Facets

The architecture should avoid one large interface and instead define a small
set of purpose-defined facets.

Recommended facets:

| Facet | Purpose | Typical users |
| --- | --- | --- |
| `ProbeFacet` | Recognize evidence and describe confidence, families, and route hints. | Source, portfolio, and statement-capable adapters. |
| `ReadFacet` | Read selected evidence and emit evidence bundles or claim bundles. | Source, portfolio, wallet, and explorer adapters. |
| `StatementFacet` | Recognize and parse statement documents plus statement-specific identity claims. | Statement-capable platform and wallet adapters. |
| `TranslateFacet` | Convert provider-local claims into bridge-ready outputs or compiler-ready claims when provider-local semantic mapping is required. | Source adapters with activity semantics. |
| `WriteFacet` | Convert runtime or projection data into target artifacts. | Output adapters. |

Additional rule:

- portfolio is not a dedicated facet
- portfolio behavior is expressed through `ReadFacet` and possibly
  `StatementFacet`, because portfolio inputs are evidence readers that emit
  balance or position claims instead of activity-heavy claims

## Responsibilities By Layer

### Adapter-Owned Responsibilities

Adapters should own only the responsibilities that truly require provider-local
knowledge.

Reader-side examples:

- identifying provider-specific evidence families
- parsing provider-specific evidence structures
- mapping provider fields into provider-local claims
- declaring provider-specific ambiguity, precision, or semantic constraints
- rendering provider-specific output labels or row shapes

Writer-side examples:

- mapping runtime semantics into target-specific row models
- handling target-specific formatting or required field population

### Shared Core Responsibilities

The shared core should own responsibilities that must be consistent across
providers.

Examples:

- evidence selection and planning
- deterministic candidate comparison and replacement rules
- stable ordering and fingerprint creation
- provenance flattening at artifact boundaries
- instrument identity resolution
- issue and review severity conventions
- fact compilation
- projection validation
- artifact writing
- replay and parity verification

### Explicit Rule

If two adapters would need the same workflow rule and that rule is not
provider-specific, it belongs in shared core services, not in duplicated
adapter logic.

## ProbeFacet Design

`ProbeFacet` should answer three questions:

1. Does this adapter recognize the evidence?
2. What evidence families or statement kinds are present?
3. What confidence and caveats apply?

It should not:

- parse the entire provider semantic model
- choose winning translation candidates
- perform full translation

The probe output should be declarative.

Recommended output fields:

- `recognized`
- `confidence_score`
- `recognized_families`
- `statement_kinds`
- `route_hints`
- `blocking_issues`
- `advisory_reviews`

This facet should replace the current spread of:

- source matching
- file-family classification
- intake matching hints
- statement-document detection

while still allowing those current jobs to be implemented incrementally.

## ReadFacet Design

`ReadFacet` is the future home for provider-local evidence reading.

Its job is to:

- accept selected evidence members
- parse them into typed evidence structures
- emit evidence bundles and claim bundles

It should not:

- own cross-provider selection policy
- infer resolved runtime instrument identity beyond provider-local claims
- write final runtime artifacts directly

Reader outputs should be deterministic for unchanged inputs.

Reader ordering rules:

- evidence members sorted by stable evidence ordering
- claims sorted by stable claim key
- diagnostics sorted by provenance plus claim or evidence id

## StatementFacet Design

Statements are important enough to deserve a specialized facet because they
have distinct evidence semantics:

- document recognition
- document parsing
- row-level balance evidence
- row-level instrument identity claims

`StatementFacet` should:

- recognize statement documents
- parse statement rows into typed statement claims
- preserve document-level and row-level provenance
- declare statement-specific ambiguity when quantity evidence is insufficient

It should not:

- silently promote valuation-only rows into quantity-backed balance references
- bypass the shared statement extraction orchestration

## TranslateFacet Design

`TranslateFacet` exists because provider-local semantics still matter even
after parsing.

Its job is to:

- convert provider-local claims into bridge-ready data or
  semantic-compiler-ready claims
- express provider-local semantic ambiguity explicitly

It should not:

- choose evidence members by itself
- resolve final runtime identities through provider-local lookup tables when shared
  resolution should own the final choice
- write output artifacts directly

This facet is closest to the current source translation behavior, but it should
operate on claims and evidence bundles rather than on raw file-path heuristics.

## WriteFacet Design

`WriteFacet` is the future unified writer surface for output adapters.

Its job is to:

- declare what semantic or projection data it accepts
- declare target-specific constraints
- emit projection bundles and artifact bundles

It should not:

- reinterpret runtime facts semantically
- invent missing projection metadata silently
- coerce unsupported fact shapes into target rows

This is a stricter version of the current output adapter model.

## Planner And Selection Model

Selection is one of the most important shared behaviors and must not remain
adapter-local.

### Design Rule

The core planner owns evidence selection. Adapters describe candidates.

### Candidate Model

Every reader capable of overlapping or replaceable evidence should be able to
describe candidates with:

- candidate id
- selection group
- family id
- member list
- coverage window
- freshness
- selection mode
- comparability
- content fingerprint
- description
- notes

### Selection Modes

The future model should preserve the useful ideas already present:

- appendable range
- replaceable range
- exclusive snapshot

Additional rules:

- candidate comparison rules must be deterministic
- unknown coverage must block selection when it could change semantics
- incomparable candidates must block selection unless an explicit human choice
  exists
- replacement must leave an auditable chain

### Why Selection Must Be Shared

If adapters choose winners internally:

- behavior becomes non-uniform
- replacement semantics drift
- test coverage becomes fragmented
- replay confidence falls

## Claim Taxonomy

The future architecture should separate provider-local claims by job.

Recommended claim families:

| Claim family | Purpose |
| --- | --- |
| `ActivityClaim` | A provider-local economic activity candidate with raw semantic details. |
| `BalanceObservationClaim` | A quantity-backed balance or position observation tied to evidence. |
| `OwnershipClaim` | A claim that a location identifier is controlled or owned. |
| `LocationClaim` | A provider-local claim about where activity, balances, or positions are held. |
| `StatementClaim` | A parsed statement row or document-level claim. |
| `InstrumentIdentityClaim` | One provider-local identity assertion for an asset or instrument. |
| `ContractTermClaim` | A provider-local claim about instrument or position terms that later economic compilation may need. |
| `ValuationClaim` | A provider-local valuation observation with purpose, time, and provenance. |
| `ProjectionAnnotation` | Output-oriented metadata that is not itself a bridge or downstream runtime fact. |
| `IssueCandidate` | A blocking or informational problem requiring shared issue assembly. |
| `ReviewCandidate` | A review-needed case requiring shared review assembly. |

These claim families let the core compiler distinguish:

- hard semantic assertions
- evidence observations
- identity claims
- output hints
- workflow diagnostics

## Shared Compilation Rules

The compiler from claims to bridge or downstream runtime data should be shared.

### Compiler Responsibilities

- resolve instrument identity from claims
- validate temporal conventions
- validate leg shape rules
- validate required location identity
- separate blocking issues from advisory reviews
- create current bridge facts, balance references, and location inventory

### Compiler Rules

- no bridge fact may be created when identity remains unresolved
- no quantity-backed balance reference may be created from valuation-only
  evidence
- no location inventory record may be created without identifier-rooted
  runtime location identity
- no output hint may become a semantic fact just because a writer can use it

### Why This Must Be Shared

If each adapter compiles bridge facts differently:

- semantic correctness becomes adapter-dependent
- output parity becomes unstable
- reconciliation trust is reduced

## Determinism Contract

Determinism must be explicit across all adapter products.

### Deterministic Inputs

For unchanged evidence, unchanged manifest versions, and unchanged shared-core
versions:

- selected evidence members must be identical
- candidate and plan fingerprints must be identical
- claim bundle fingerprints must be identical
- bridge or runtime dataset fingerprints must be identical
- projection bundle fingerprints must be identical
- artifact fingerprints must be identical unless the target format includes a
  documented nondeterministic field that is intentionally excluded

### Deterministic Ordering Rules

Every adapter product must declare a sort key.

Examples:

- evidence members sorted by stable provenance key
- candidates sorted by selection group, coverage, freshness, and candidate id
- claims sorted by claim family, timestamp, stable claim id, and provenance
- facts sorted by timestamp, effective time, source, fact id
- issues and reviews sorted by severity, kind, timestamp, provenance, id
- projection rows sorted by target-defined stable row order

### Fingerprint Rules

Every adapter product should have:

- a schema version
- a stable serialization form
- a stable fingerprint

Serialization rules should:

- sort object keys
- avoid implicit ordering from language runtime containers
- exclude presentation-only noise
- include semantically relevant fields only

## Assertions, Issues, And Reviews

The future design should treat diagnostic surfaces as first-class contracts.

### Hard Assertions

Hard assertions are required for bridge or runtime acceptance.

Examples:

- one resolved instrument identity
- valid timezone semantics
- valid quantity precision where required
- acceptable leg shape

### Blocking Issues

Blocking issues stop bridge acceptance or later workflow progress.

Examples:

- ambiguous identity
- unsupported precision loss
- unknown coverage during candidate selection
- incompatible evidence bundles in one selection group

### Reviews

Reviews are explicit human attention requests that do not always block the
entire workflow.

Examples:

- lower-confidence fee precision on a known provider edge
- advisory same-source same-chain portfolio evidence
- low-confidence ownership inference

### Rule

Adapters must not downgrade a hard semantic failure into a review just to keep
facts flowing.

## Provenance Model

Provenance is central enough to deserve explicit rules.

### Runtime Rule

Provenance stays typed in runtime models until artifact boundaries.

### Provenance Levels

The future model should distinguish:

- evidence member provenance
- parsed row or page provenance
- claim provenance
- bridge or runtime derivation provenance
- artifact derivation provenance

### Why Product Boundaries Matter

The repo needs to answer:

- which file, sheet, row, or page caused this fact
- which evidence item supports this balance reference
- which candidate was selected and why
- which target row came from which fact or claim

Ad hoc string fields are not enough for that.

## Identity Model

Identity rules should remain shared and identifier-rooted.

### Instrument Identity

Adapters should emit identity claims, not final resolved runtime instrument
choices.

The shared identity resolver should:

- accept multiple claims
- resolve exactly one runtime instrument or fail explicitly
- preserve review context when ambiguity remains

### Location Identity

Adapters should emit identifier-rooted runtime locations.

Rules:

- friendly labels stay out of runtime ids
- chain or network identity must be explicit
- sublocations must be stable derivations of parent identity

### Ownership

Ownership claims should be their own claim family, not hidden in translation
helpers.

## Temporal And Numeric Policy

Time and quantity interpretation must be explicit at the adapter edge, but the
policy model should be shared.

### Temporal Rules

- timestamps must be timezone-aware before entering bridge or downstream
  runtime data
- date-only and timestamp precision must remain distinct
- exact midnight timestamps are still timestamps if the source contract says so
- unknown or conflicting timezone interpretation must block or review
  explicitly based on declared policy

### Numeric Rules

- financial quantities remain `Decimal`
- precision expectations may be declared by manifest or provider-local code
- silent rounding or truncation is not acceptable on semantically important
  quantities
- known provider precision defects must be modeled as explicit review or issue
  behavior

## Input, Portfolio, And Output Under One Model

The future design should stop treating input, portfolio, and output as
fundamentally different architecture categories.

### Input

An input adapter is an adapter whose facets read evidence and emit claims,
bridge-ready outputs, or downstream runtime data.

### Portfolio

A portfolio adapter is an input adapter whose primary claim types are balance,
position, statement, or ownership claims instead of activity-heavy claims.

### Output

An output adapter is an adapter whose primary facet writes projection or
artifact bundles from runtime or projection data.

### Why One Adapter Model Matters

The architecture stays smaller if:

- one manifest model describes all adapters
- one verifier model checks their products
- one shared adapter vocabulary describes the flow

## Migration Of Current Jobs Into Future Facets

The current repo jobs should map into the future architecture as follows.

| Current job | Future owner |
| --- | --- |
| profile matching | `ProbeFacet` plus shared selection service |
| file-family classification | `ProbeFacet` plus manifest-declared evidence families |
| intake matching and route hints | `ProbeFacet` plus shared intake router |
| timezone summary | shared temporal policy service with manifest-declared expectations |
| location inventory extraction | `ReadFacet` or `TranslateFacet` producing `OwnershipClaim` and runtime inventory through shared compilation |
| statement matching and parsing | `StatementFacet` plus shared statement orchestration |
| translation-input planning | shared planner using manifest and candidate descriptions |
| activity translation | `ReadFacet` and `TranslateFacet` producing `ActivityClaim` |
| draft compilation | shared compiler to current bridge outputs first, then `EconomicFacts` once the bridge is retired |
| output policy validation | shared projection validator |
| rendering | `WriteFacet` |

This mapping is the main path for shrinking adapter entry points.

## Testing And Verification Model

The future adapter system needs a stronger and more uniform verification model
than the current contract-by-contract mixture.

### Required Test Layers

| Layer | Purpose |
| --- | --- |
| Unit tests | Provider-local parsing, semantic mapping, and edge-case decisions. |
| Contract tests | Manifest validity, facet declarations, and product schema conformance. |
| Golden tests | Stable evidence, claim, economic, and projection outputs on known packs. |
| Replay tests | Re-run unchanged inputs and verify identical stable fingerprints. |
| Negative tests | Assert blocking behavior for unsupported or ambiguous evidence. |

### Mandatory Determinism Checks

- shuffled file order must not change selected candidates
- equivalent archive extraction order must not change claim order
- repeated runs must preserve stable fingerprints
- rendered writer outputs must remain stable for unchanged economic datasets

### Compatibility Checks

The future verifier should check:

- manifest schema compatibility
- adapter product schema compatibility
- adapter support-window declarations
- intentional breaking changes via explicit version increments

## Scaffolding And Authoring Rules

Once the future model lands, scaffolds should create:

- one manifest
- only the facets the adapter actually implements
- provider-local modules split by real concern
- local tests for each implemented facet

Scaffolds should not create:

- no-op method surfaces for unrelated jobs
- fake fallback methods just to satisfy a bundled protocol
- generic helper dumps

## Performance And Operational Rules

The future system should optimize for determinism first and performance second,
but performance still matters.

Rules:

- bundle products should be stream-friendly where possible
- large evidence collections should avoid materializing unnecessary duplicate
  structures
- fingerprints should be cheap enough to run in ordinary workflows
- shared planning should avoid repeated provider-local rescans when profile
  artifacts already contain the needed evidence facts

## Security And Safety Posture

The adapter system should remain safe-by-default.

Rules:

- adapters may read only selected evidence provided by the core workflow
- adapters should not perform unrestricted workspace scans outside their
  assigned evidence roots
- network calls should remain outside ordinary adapter reading unless a
  separate provider family explicitly owns them
- ambiguity should never be hidden for convenience

## Open Questions

These questions are intentionally left open for later design review:

- Should `ReadFacet` emit evidence bundles and claim bundles separately, or may
  some adapters emit claims directly when parsing is trivial?
- Should writer adapters consume `EconomicFacts` directly, or should all
  writers consume a target-neutral `ProjectionBundle` first?
- Which manifest fields should be purely declarative versus code-generated?
- How much of current timezone and precision policy belongs in manifest data
  versus provider-local code?
- Should claim and product fingerprints include manifest fingerprints
  directly, or reference them externally?

These are implementation questions, not reasons to keep the bundled current
contract.

## Migration Principles

When this architecture is implemented later, migration should follow these
rules:

- adapter product and bridge-mapping contracts may advance during shared
  foundations when the first target-stage slice needs them
- migrate by adapter family, not all at once
- do not preserve permanent dual contracts
- keep each checkpoint reviewable
- let filing-critical adapters migrate first only after the filing path is
  stable
- remove obsolete seams once the new family path is verified

## Practical Near-Term Guidance

Until the future architecture lands:

- keep current adapter changes moving toward these product and facet
  boundaries
- extract shared workflow logic when it is clearly cross-provider
- avoid adding new adapter-local orchestration that the future shared planner,
  compiler, or verifier should own
- keep current fixes filing-first while still using this document as the
  direction of travel

## Design Summary

The future adapter architecture should be:

- manifest-centered
- facet-based
- intermediate-representation driven
- deterministic by contract
- provenance-rich
- issue-forward
- migration-friendly

It should not be:

- monolithic
- filename-order driven
- tracker-centered
- adapter-local workflow heavy
- tolerant of hidden ambiguity

## External Design References

These references support the design posture in this document.

- Alistair Cockburn, Hexagonal Architecture:
  <https://alistair.cockburn.us/hexagonal-architecture>
- MLIR Dialect Conversion:
  <https://mlir.llvm.org/docs/DialectConversion/>
- Apache Avro Specification:
  <https://avro.apache.org/docs/1.12.0/specification/>
- Apache Beam coder determinism:
  <https://beam.apache.org/releases/pydoc/2.10.0/apache_beam.coders.coders.html>
- RFC 8785 JSON Canonicalization Scheme:
  <https://www.rfc-editor.org/rfc/rfc8785>
- W3C PROV-DM:
  <https://www.w3.org/standards/history/prov-dm/>
- JSON Schema Draft 2020-12:
  <https://json-schema.org/draft/2020-12>
