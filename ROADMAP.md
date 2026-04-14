# ROADMAP

This file is the forward planning document for the repo.

- Completed work belongs in [CHANGELOG.md](CHANGELOG.md).
- The currently implemented runtime surface belongs in
  [`docs/status/current-state.md`](docs/status/current-state.md).
- Architectural decisions, schema contracts, and migration rules belong in the
  architecture docs, especially:
  - [`docs/concepts/reconciliation-tax-architecture.md`](docs/concepts/reconciliation-tax-architecture.md)
  - [`docs/status/migration-sequence.md`](docs/status/migration-sequence.md)
  - [`docs/concepts/oracle-boundaries.md`](docs/concepts/oracle-boundaries.md)
  - [`docs/concepts/transaction-classification.md`](docs/concepts/transaction-classification.md)

This roadmap assumes the repo stays on the current fact-based architecture. It
tracks remaining phases, sequencing, and delivery gates. It does not restate
the detailed architecture contract.

The current runtime now uses `application/balances` as the shared balance
capability across normalization, reconciliation, and checkpoint submission.
Inspect, check, and summarize are the operator-facing balance commands.
Balance state is expressed as derived `balance_snapshots.csv` plus unified
`balance_references.csv`, where each reference row declares its
`reference_kind`. Fact-backed checks derive snapshots from facts;
manual-only checks consume explicit snapshot rows; check runs offline by
default and hydrates only when requested.

Historical provider hydration is now a first-class balance concern, but the
current implementation target remains public-ledger balance lookup only. The
current codebase also ships the separate balance-provider discovery seam with
discoverable `evm_json_rpc` and `near_rpc` family stubs, plus native and
contract-backed public-ledger asset ids for the in-scope EVM, NEAR, and Ronin
adapters. Live network hydration remains deferred behind provider
implementations.

## Planning Anchors

These planning anchors drive phase order and acceptance criteria:

- the historical CoinTracking export boundary around `2023-08-05` remains an
  oracle boundary, not a trusted opening checkpoint
- the first source-backed checkpoint target remains near `2026-03-23`
- the filing-critical output horizon remains `2023` through `2025`
- reconciliation remains the trust gate before tax
- accounting validates journal structure and coverage in parallel with
  reconciliation once the fact path is stable
- capture identity is metadata, not path
- typed provenance stays a runtime model and is flattened only when writing
  artifacts
- normalization is capture-scoped and reconciliation is source-assembly-scoped
- raw-evidence derivation is the supported semantic parity path

## Detailed Pipeline Delivery Plan

The numbered phases below remain the coarse rollout gates. The detailed plan in
this section is the implementation reference for the target pipeline products
and the bounded slices needed to land them without ad hoc design during coding.

Use the exact target product names from
`docs/concepts/reconciliation-tax-architecture.md` when shaping the next
contracts:

1. `EvidenceSet`
2. `ClaimSet`
3. `EconomicFacts`
4. `ReconciliationState`
5. `Checkpoint`
6. `Journal`
7. `TaxInputs`
8. `TaxOutputs`

### Cross-Cutting Contracts To Land Before Broad Pipeline Expansion

These contracts should be treated as blocking shared foundations rather than as
optional cleanup.

Scope:

- one typed provenance family across evidence, claims, balances, issues,
  reviews, checkpoints, accounting, and tax artifacts
- one controlled gap taxonomy with stage ownership, blocking scope, subject
  references, candidate interpretations, required evidence, and allowed
  resolution methods
- one readiness vocabulary reused across all datasets
- one shared slice model for readiness and materiality
- one explicit identity seam for instrument, contract, position, location,
  legal owner, beneficial owner, and counterparty identity
- `SubjectRef` for shared infrastructure that needs a generic reference without
  flattening `Contract` and `Position`
- one typed tax-policy selection seam reused by later `TaxInputs` and
  `TaxOutputs` work
- one checkpoint assertion vocabulary reused by reconciliation, checkpoint
  adoption, accounting, and tax

Rules:

- do not let each new stage invent its own status field or bespoke blocker row
- do not store whole-dataset readiness as the only truth; derive it from
  subject-level readiness reducers
- keep gap ownership explicit so accounting gaps, reconciliation gaps, and
  tax-owned gaps are not conflated operationally

Shared readiness uses this exact slice definition:

- source
- location
- instrument
- subject ref
- continuity segment
- checkpoint date
- tax year where relevant

Exit criteria:

- shared gap and readiness models exist with typed reducers and artifact
  contracts
- every new stage can emit stage-owned gaps without inventing one-off issue
  formats
- dataset summaries derive from subject-level readiness instead of hand-built
  status prose

### MVP Scope Guardrails

The MVP should remain filing-capable, provider-neutral where it matters, and
small enough to implement without a speculative framework buildout.

Rules:

- use the current fact-plus-balances bridge until the next concrete slice needs
  a richer stage contract
- do not wait for every target product to exist before improving the active
  filing path
- add new stage models, reducers, or ports only when one bounded slice needs
  them for correctness, determinism, or later-stage reuse
- avoid plugin systems, manifest families, or broad orchestration abstractions
  before a second concrete implementation requires them
- keep unsupported or deferred behavior explicit through gaps instead of
  low-confidence partial support
- prefer one end-to-end vertical slice that proves a new stage over several
  horizontal framework layers with no proven consumer
- keep crypto filing-critical coverage primary for the MVP while using generic
  runtime names and boundaries that can later absorb other instrument classes
- keep current-contract adapter stabilization distinct from the later adapter
  redesign

Exit criteria:

- the active filing path keeps moving while the architecture becomes more
  explicit
- new reusable seams exist because one real slice needed them, not because the
  repo was trying to pre-build every future variation

### Performance Expectations

Rollout choices must preserve bounded recalculation cost.

Rules:

- expensive reducers must be partitionable by source, location, instrument,
  subject ref, continuity segment, checkpoint date, and tax year where
  relevant
- hot-path calculations should operate on compact typed records instead of
  repeatedly joining provenance, review, or renderer payloads
- derived snapshots and reusable state should be introduced where replay cost
  becomes material
- tax work should support tax-year partitioning and carry-forward reuse instead
  of recomputing full acquisition history for every output row

### Slice A. Harden `EvidenceSet`

Goal:

- make deterministic evidence selection and source-local observation capture the
  formal first pipeline product

Scope:

- carry selected, superseded, and blocked raw inputs as explicit evidence-bundle
  artifacts
- keep document, statement, and inventory observations source-local
- preserve capture, assembly, and document provenance without forcing economic
  meaning
- keep deterministic evidence selection in core planning services rather than in
  adapter-local heuristics

Primary owners:

- `application/intake/`
- `application/profiling/`
- `application/evidence/`
- `application/normalization/translation_inputs/`

Required contracts:

- deterministic evidence selection report
- source-local parsed observation contracts
- explicit superseded and blocked evidence outputs
- evidence-bundle summary and issue surfaces

Must not do:

- invent economic meaning at the evidence layer
- hide raw-selection decisions inside adapter code
- collapse source-local observations into final facts when the source remains
  ambiguous

Exit criteria:

- the runtime can explain why every selected source artifact won and why every
  superseded artifact lost
- source-local observations and their provenance survive beyond file-selection
  time
- evidence selection becomes the only supported path into later claim and
  economic compilation work

### Slice B. Introduce `ClaimSet` Without Breaking The Current Fact Path

Goal:

- interpose a source-local claim layer between evidence selection and final
  economic facts

Scope:

- define activity, balance, ownership, location, instrument, contract-term, and
  valuation claim contracts
- allow materially unclassified claims when a provider row cannot safely commit
  to one `EconomicKind`
- capture candidate interpretations and blocking ambiguity explicitly
- keep current `EconomicActivityDraft` as a transitional bridge while claim
  contracts land incrementally

Primary owners:

- `ports/source_translation.py`
- `application/facts/`
- source adapters under `adapters/sources/`

Required contracts:

- claim bundle aggregate
- claim-to-economic compilation seam
- claim-owned issue and review contracts
- explicit mapping from transitional draft fields into claim semantics during
  migration

Must not do:

- require every claim to carry final economic, tax, and accounting semantics
- bind ambiguous transfers, ownership changes, restructurings, or mixed rows to
  one interpretation just to stay on the current draft shape
- let adapters widen policy responsibility beyond source-local meaning

Exit criteria:

- at least one adapter family emits claim-native outputs before economic
  compilation
- ambiguous source rows can remain claim-complete but economically unresolved
- the compiler can reject unsafe claims without losing claim provenance

### Slice C. Expand `EconomicFacts` Beyond Today’s Minimal Fact Shape

Goal:

- make the economic-truth layer broad enough for obligation-bearing and
  lifecycle-heavy instruments

Scope:

- keep `TransactionFact` as the current row-level bridge while expanding the
  economic dataset contract around it
- add first-class seams for contract instance identity, ownership change
  semantics, settlement state, supersession, collateral, financing, and
  lifecycle events
- add valuation attachments with purpose, time, source, precision, and
  provenance instead of free-form downstream valuation assumptions
- keep signed-leg structure, precision, and provenance strict

Primary owners:

- `domain/transactions/`
- `domain/instruments/`
- `application/facts/`

Required contracts:

- economic dataset aggregate contract
- contract instance or position identity surface
- valuation attachment contract
- correction and supersession chain contract

Must not do:

- assume all activity is spot movement between wallets and exchanges
- encode loans, margin, shorts, options, futures, repos, or corporate actions
  as awkward spot-only special cases
- treat output-adapter projection hints as the long-term driver of core
  behavior

Exit criteria:

- economic facts preserve the determinants needed for later reconciliation,
  accounting, and tax work without revisiting raw rows
- at least one non-trivial obligation or lifecycle-heavy activity family is
  representable without a local special-case rewrite
- valuation requirements are explicit rather than inferred ad hoc downstream

### Slice D. Build `ReconciliationState` As Its Own Product

Goal:

- make reconciliation more than exact balance assertions by defining the
  completeness and continuity product

Scope:

- transfer linking across owned venues and wallets
- funding and settlement completeness checks
- continuity windows and unresolved ownership transitions
- cross-source corroboration sidecars
- reconciliation-owned gaps, readiness, and clean-window summaries
- checkpoint candidate assembly inputs

Primary owners:

- `application/reconciliation/`
- `application/balances/`

Required contracts:

- reconciliation dataset aggregate
- explicit link records and link-decision artifacts
- continuity-window and clean-window artifacts
- missing-leg and unresolved-transition artifacts

Must not do:

- rewrite upstream economic facts just to satisfy a check
- erase valid partial balances because the full source window is not yet clean
- collapse transfer-link uncertainty into tax or accounting-owned logic

Exit criteria:

- exact balance assertion output becomes one reconciliation surface, not the
  entire reconciliation product
- transfer links, continuity gaps, and checkpoint candidates are explicit
  runtime artifacts
- reconciliation readiness is sliceable by source and time window

### Slice E. Formalize `Checkpoint`

Goal:

- make accepted checkpoint truth a first-class package boundary and not only a
  derived summary

Scope:

- checkpoint assertion contracts
- acceptance basis and trust-level contracts
- intentional opening-state adoption flow with provenance
- continuity into the adopted checkpoint
- checkpoint summaries reusable by accounting and tax

Primary owners:

- `application/checkpoints/`
- `domain/checkpoints/`
- `application/reconciliation/`

Required contracts:

- accepted checkpoint package
- opening-state adoption package
- checkpoint evidence index
- checkpoint continuity report

Must not do:

- treat operator assertions as equivalent to filing-ready source-backed
  checkpoint evidence
- leave accepted checkpoint state implicit in reconciliation notes or balances
  summaries

Exit criteria:

- one checkpoint package can be referenced directly by later accounting and tax
  workflows
- checkpoint acceptance basis is explicit and auditable
- opening-state adoption is intentional, reviewable, and provenance-backed

### Slice F. Build `Journal` As A Validator, Not A Truth Repair Layer

Goal:

- expand accepted upstream truth into double-entry structure and expose
  accounting coverage gaps explicitly

Scope:

- posting assembly from reconciled economics and accepted checkpoint state
- journal validation artifacts
- unsupported accounting coverage gap reporting
- checkpoint-aligned accounting summaries

Primary owners:

- `domain/accounting/`
- `application/accounting/`
- output renderers under `application/outputs/` and adapter layers

Required contracts:

- journal dataset aggregate
- posting contract
- validation result contract
- accounting coverage gap contract

Must not do:

- patch upstream truth locally to make the ledger balance
- treat renderer-specific chart choices as the domain model
- make tax depend on renderer success when the underlying determinants are
  already known

Exit criteria:

- balanced supported activity renders deterministically
- unsupported accounting coverage is visible as stage-owned gaps
- accounting outputs can be reconciled back to accepted checkpoint state

### Slice G. Introduce `TaxInputs`

Goal:

- separate policy-ready tax inputs from both raw economics and final
  jurisdiction outputs

Scope:

- acquisition and disposition determinants
- income-event determinants
- internal transfer determinants
- financing-cost determinants
- basis or pool state transitions
- valuation requirements for tax computation
- tax-owned unresolved gaps

Primary owners:

- `domain/tax/`
- `application/tax/`

Required contracts:

- tax-input aggregate
- determinant-to-policy application seam
- tax-owned gap contract
- year-state and carry-forward intermediate contracts

Must not do:

- branch tax logic directly on CoinTracking or other oracle artifact rows
- use journal output as a hidden prerequisite when the journal only restates
  already-known truth
- fill missing valuations or ownership decisions silently

Exit criteria:

- the runtime can explain what was acquired, disposed, earned, transferred
  internally, or still unresolved before jurisdiction rules render final output
- tax-owned gaps are distinguishable from reconciliation and accounting gaps
- determinant coverage is reproducible from reconciled economics plus accepted
  checkpoint truth

### Slice H. Build `TaxOutputs`

Goal:

- render jurisdiction-specific outputs from determinants without contaminating
  earlier stages with jurisdiction rules

Scope:

- Canada MVP outputs first
- year summaries
- carry-forward outputs
- explicit unsupported and deferred outputs

Primary owners:

- `application/tax/`
- output renderers under `application/outputs/`

Required contracts:

- tax output aggregate
- jurisdiction renderer contracts
- unsupported-output reporting

Exit criteria:

- `2023`, `2024`, and `2025` outputs emit from `TaxInputs` through selected
  policy
- carry-forward state is deterministic and reproducible
- unresolved unsupported items remain visible instead of disappearing into
  notes

### Slice I. Cross-Stage Verification And Retirement

Goal:

- replace transition-era behavior only after the new pipeline products prove
  themselves end to end

Scope:

- raw-evidence semantic parity validation
- reconciliation artifact parity where meaningful
- checkpoint continuity regression coverage
- journal validation coverage
- tax determinant and output coverage
- retirement of normalized-transaction-era assumptions after the fact-native
  path is stable

Rules:

- do not remove an older path until the replacement has stage-appropriate
  parity, contract, and smoke coverage
- prefer replacing one active runtime path with a new typed product over adding
  long-lived wrapper lanes

Exit criteria:

- the supported workflow runs from source evidence through tax output without
  transition-only assumptions
- remaining compatibility surfaces are deliberate edges, not hidden core
  dependencies

## Roadmap Sequence

### 1. Oracle Boundary Completion

Finish the remaining dev-only oracle support needed for comparison,
regression, and filing-close validation.

Scope:

- complete boundary models for the supported CoinTracking oracle artifact
  families
- complete deterministic readers and comparison-ready artifact contracts under
  the dev-only oracle tooling surface
- finish oracle comparison coverage needed for filing-close validation

Exit criteria:

- supported oracle files parse deterministically
- oracle comparison workflows are complete enough to support later filing-close
  validation
- oracle support remains outside the production runtime surface

### 2. Fact-Path Stabilization Before Deeper Trust Work

Finish the remaining fact-path follow-through required before broad
reconciliation, accounting, and tax work expands.

Scope:

- keep direct fact artifacts as the only runtime model
- treat filing-critical adapter work as a stabilization track on the current
  seams: during the filing window, prioritize deterministic planner, evidence,
  translation, and output hardening for the adapters actually used by the
  active filing workflow, and defer the broader unified adapter contract
  rewrite until after that path is stable; treat
  `docs/concepts/unified-adapter-architecture.md` as the explicit design
  target for later adapter-contract replacement
- center intake on explicit capture identity, capture registries, and
  raw-evidence preservation instead of inferred capture buckets
- keep inferred period and capture heuristics as report metadata only; they do
  not control runtime identity, routing, or normalization ownership
- finish adapter parity and projection parity coverage on the current fact
  model
- keep file-selection policy in `application/normalization/` rather than in
  adapter-local filename or path-order heuristics
- keep review and issue outputs explicit for ambiguous direction, precision, or
  classification decisions
- persist translation planner artifacts showing candidate descriptions, plan
  decisions, and blocking issues before translation begins
- continue tightening overlap heuristics, duplicate detection, file-family
  signatures, and capture acceptance rules where capture ownership is still
  ambiguous
- split capture-scoped normalization from source-scoped assembly before
  reconciliation expands further
- centralize statement extraction, document discovery, provenance, and shared
  issue or review handling behind one evidence seam
- keep statement selection and portfolio evidence dating owned by typed capture
  and profile metadata rather than by capture-label conventions or raw-path
  rescans
- allow adapter-owned upstream workbook exports to remain raw evidence when the
  typed intake route classifies them as source originals
- keep source profile and source normalize strict to one materialized raw
  capture root and fail explicit on arbitrary directories or mismatched capture
  metadata
- make source assembly rerun-safe by rewriting its owned generated artifact
  surface deterministically on each run
- migrate adapters to the planner path in stages, starting with Coinbase and
  then other adapters that still pick one export by filename or path heuristic
- add a repo-native semantic parity validator for unchanged raw inputs
- keep the broad adapter-interface redesign documented and deferred while
  filing-critical adapters remain on the current contract; use that later
  redesign to replace the bundled source contract only after the active filing
  path is deterministic enough to trust
- define the target `EvidenceSet` and `ClaimSet` contracts and land them
  incrementally without reintroducing normalized-transaction-era wrappers
- allow source-local ambiguity to survive into claim outputs when forcing one
  final economic meaning would guess
- keep `EconomicActivityDraft` and `TransactionFact` as transition seams rather
  than freezing them as the final architecture center

Exit criteria:

- supported adapters emit facts without normalized-transaction-era wrapper
  lanes
- planner-enabled adapters no longer choose winning translation inputs by path
  order or lexical filename order
- selected, superseded, and blocked translation inputs are explicit
  normalization artifacts before fact translation runs
- CoinTracking CSV projection remains correct from facts alone
- remaining normalization ambiguity paths emit explicit reviews or blocking
  issues instead of silent coercion
- balance references, issue rows, review rows, and location inventory evidence
  rows share one flattened provenance locator family at artifact boundaries
  while runtime models keep typed provenance
- at least one adapter family proves the claim-to-economic compilation path
  without requiring every claim to bind final tax and accounting intent early
- unchanged raw inputs preserve file completeness, fact counts, snapshot
  counts, reference counts, and issue or review counts unless an
  expected-difference fixture documents the exception
- expected-difference fixtures may relax only issue-count or review-count
  parity and must never excuse raw completeness, fact, snapshot, reference, or
  reconciliation drift

### 3. Reconciliation

Build deterministic reconciliation on top of transaction facts, derived
balance snapshots, and unified balance references.

Scope:

- read only assembled source datasets produced from accepted captures
- keep target planning, snapshot derivation, reference resolution, inspect and
  check workflows, hydration, and assertion assembly behind the shared balance
  capability
- extend the first exact balance assertion workflow into broader checkpoint and
  transfer checks
- keep statement-backed quantity evidence on the normalization path and treat
  valuation totals as out of scope
- accept `balance_snapshots.csv` plus unified
  `balance_references.csv` from normalization, manual submission, or later
  provider hydration without splitting the downstream reconciliation contracts
- keep historical API lookup behind separate balance-provider adapters instead
  of extending source adapters
- require on-chain asset ids with immutable chain identity before public-ledger
  provider hydration is considered supported
- keep symbol-only public-ledger asset ids as explicit unsupported surfaces
  rather than soft-mapping them into provider hydration
- add additive cross-source corroboration as a sidecar evidence surface before
  promoting it into a harder reconciliation gate
- transfer linking across owned wallets and exchanges
- checkpoint continuity checks
- correction and supersession chains
- reconciliation issue assembly
- define `ReconciliationState` as an explicit product with link decisions,
  continuity windows, checkpoint candidates, and reconciliation-owned readiness
  slices rather than treating exact balance assertions as the whole product
- deterministic correction handling for known historical events such as the
  GALA redistribution

Exit criteria:

- exact balance assertion artifacts are stable and feed later continuity checks
- additive cross-source corroboration artifacts exist without redefining the
  primary clean-date gate and remain dependent on comparable location identity
- fact history can be reconciled against source-backed evidence or
  operator-confirmed balance references without manual tracker logic
- reconciliation inputs no longer depend on raw capture layout or direct
  multi-capture crawling
- reconciliation artifacts no longer depend on normalized-transaction-era
  stopgaps
- material reconciliation issues surface explicitly and reproducibly
- reconciliation readiness is reducible by source, location, instrument, and
  continuity window instead of only by coarse source summaries

### 4. Checkpoint And Opening State

Formalize typed checkpoints as the handoff between reconstruction,
reconciliation, accounting, and tax.

Scope:

- checkpoint artifact contracts
- checkpoint provenance and evidence requirements
- keep manual/operator-authored balance submission packages as a supported
  checkpoint-owned input path for balance snapshots and operator assertion
  references
- keep manual submission row contracts boundary-validated and derive
  `location_id` values through shared helpers instead of handwritten generic
  ids
- source-backed checkpoint builder centered on the best-supported balance date
  near `2026-03-23`
- intentional opening-state adoption flow with provenance
- continuity checks between reconstructed balances and adopted checkpoints
- keep checkpoint trust level and acceptance basis explicit so later accounting
  and tax work can reference accepted checkpoint truth directly

Exit criteria:

- an operator-authored runtime balance package can be created and reused as a
  typed input without weakening the later source-backed checkpoint requirement
- opening-state adoption is explicit, auditable, and not dependent on operator
  memory
- checkpoint continuity reports exist as first-class artifacts

### 5. Accounting Validation

Advance accounting in parallel once reconciliation contracts are stable enough
to support journal projection.

Scope:

- internal journal model
- renderer port
- Ledger CLI renderer
- journal validation result artifacts
- accounting summaries tied to reconciliation and checkpoint outputs
- keep accounting coverage gaps stage-owned and explicit instead of repairing
  upstream truth locally

Exit criteria:

- supported activity renders deterministically in Ledger CLI
- Ledger CLI parse and balance validation passes for supported activity
- accounting outputs can be checked against checkpoint balances

### 6. Canadian Tax Policy

Implement the first tax policy only after reconciliation establishes a trusted
fact history and checkpoint basis.

Scope:

- tax policy port
- Canada MVP policy
- tax-input contracts between reconciled economics and rendered tax outputs
- pooled ACB state
- disposition outputs
- income outputs
- unsupported tax item outputs
- carry-forward and year summary outputs for `2023`, `2024`, and `2025`
- keep tax-owned unresolved determinants explicit rather than encoding them as
  generalized reconciliation or accounting failures

Exit criteria:

- `2023` to `2025` tax outputs emit from `TaxInputs` built from reconciled
  economics plus accepted checkpoint truth
- year-end and carry-forward state is reproducible without tracker tax reports
- unresolved unsupported tax items are visible rather than hidden in notes
- tax inputs are reproducible from reconciled economics plus accepted
  checkpoint truth without depending on CoinTracking or other oracle rows

### 7. Filing Workflow

Assemble the full filing-capable workflow after reconciliation, checkpoints,
accounting, and tax each have a working typed slice.

Scope:

- end-to-end filing workflow from source evidence to tax outputs
- checkpoint continuity gate
- oracle comparison against historical CoinTracking tax outputs
- explicit deferred-case capture for anything still unsupported

Exit criteria:

- the forward-computed state from the `2023-08-05` oracle boundary lands on the
  source-backed checkpoint near `2026-03-23`
- `2023`, `2024`, and `2025` outputs are reproducible from workspace evidence
- no unresolved material reconciliation issues remain
- no unresolved material unsupported tax items remain

### 8. Transition Retirement And Parity Closeout

Retire or demote the remaining normalized-transaction-era transition surfaces
after the filing-critical path is stable.

Scope:

- remove remaining normalized-transaction-first assumptions from active runtime
  workflows
- keep parity coverage in place until older transition surfaces are retired
- keep CoinTracking output available as an ordinary output adapter after the
  transition path is removed

Exit criteria:

- reconciliation, accounting, and tax all consume fact-native workflows
- no active runtime slice still depends on normalized-transaction-era
  assumptions
- new behavior lands on fact-based services first

### 9. Public Repo And Agent Hardening

Finish the post-filing documentation and repository hardening needed for a
public, agent-usable codebase.

Scope:

- sanitize and maintain publishable fixtures
- keep provenance and reuse documentation clear
- keep the docs set navigable by type and concern
- keep public-facing scope descriptions aligned with the implemented runtime
- keep delivery guardrails layered across platform settings, repo-native
  validators, and agent defaults so repo policy does not depend on prose alone
- keep control-plane ownership routing and default-branch guardrail audits
  explicit so local repo state and live GitHub protection drift are checked
  together
- keep repo-native PR review routing, change-sensitive PR-only review checks,
  and explicit changed-surface coverage aligned so review loops do not stop
  early after only inspecting a narrow subset of the touched surfaces
- keep quality-gate scheduling benchmark-backed and push CI split into explicit
  lint, type, pylint, test, and build jobs instead of one opaque parity shell

Exit criteria:

- repo-safe fixtures and documentation are maintained without private workflow
  assumptions
- a new contributor or coding agent can find the correct roadmap, status,
  concept, guide, and workspace docs without broad context loading
- the default-branch delivery path is enforced by platform and repo controls
  strongly enough that a single agent mistake cannot silently bypass the
  intended PR-only workflow
- the repo can audit local CODEOWNERS coverage and live GitHub delivery
  settings together without broad context loading or one-off shell repair work

### 10. Post-Core Runtime Expansion

Only after the filing-critical path is stable should the repo expand runtime
surfaces and storage choices.

Scope:

- thin HTTP or agent-facing interfaces over the same typed application
  contracts
- SQLite-backed active storage behind repository ports
- provider-backed AI implementations with explicit audit trails
- additional productized source and output adapters beyond the current
  high-value evidence sources

## Cross-Cutting Workstreams

These workstreams continue across the major phases above.

### Oracle Lane

- keep CoinTracking report readers and comparison tooling under `tools/oracles/`
- use oracle artifacts for regression, black-box comparison, and historical
  review only
- never let oracle files become hidden production dependencies

### Adapter Completion

- complete parity coverage for supported source adapters on the fact model
- tighten overlap heuristics, duplicate detection, and file-family signatures
  where capture ownership remains ambiguous
- extend shared adapter support only where it removes repeated provider-local
  workflow code

### Verification And Tests

- maintain parser and adapter contract tests
- expand projection parity tests
- keep semantic parity, capture-registry, and source-assembly coverage as
  first-class regression surfaces
- add reconciliation parity and checkpoint continuity tests
- add Ledger CLI validation coverage
- add Canadian tax policy coverage including fees, income, realized PnL, and
  unsupported-item reporting
- keep end-to-end smoke workflows for each major slice before removing older
  transition paths

### Test Preservation

- no test deletions without explicit human approval
- no silent assertion removal
- no fixture simplification that hides previous edge-case coverage
- test relocation or renaming is acceptable only when behavior coverage is
  preserved or improved
- "updating tests to the new structure" is not acceptable if coverage is
  weakened
- every refactor slice that changes tests must state:
  - what old behavior the tests covered
  - where that same behavior is covered now
  - whether the assertion got stronger, weaker, or simply moved
  - whether any expectation changed because of an intentional product decision
- require a `test parity note` in checkpoint summaries
- require manual review of deleted test files, deleted assertions, reduced
  scenario coverage, and fixture simplifications that remove edge cases

### Repo And Package Shaping

- continue splitting hotspot modules and DTO hubs before new reconciliation,
  checkpoint, accounting, and tax behavior piles into flat files
- escalate helper clusters into packages once a third related sibling would
  otherwise appear
- preserve bounded submodules in existing shared surfaces
- keep newer workflow seams such as `application/profiling/` and
  `application/intake/plan/` as packages as they grow

## Filing-Critical Acceptance Criteria

The system is filing-ready only when all of these are true:

- a source-backed checkpoint exists near `2026-03-23`
- no unresolved material reconciliation issues remain
- no unresolved material unsupported tax items remain
- Ledger CLI validation passes for supported activity
- the forward-computed state from the `2023-08-05` oracle boundary lands on the
  source-backed checkpoint
- `2023`, `2024`, and `2025` outputs can be reproduced from workspace evidence

## Deferred Until Core Rollout Lands

### HTTP, API, And Agent Runtime

- add a thin HTTP layer only over existing application capabilities and typed
  use-case contracts
- keep CLI, API, and agent requests on the same service contracts
- move interface contracts toward resource-oriented request and response shapes
- prefer explicit job handles and artifact references for long-running work

### Database Adoption

- replace filesystem-backed fact and evidence storage with a SQLite-backed
  implementation behind repository ports
- keep raw evidence as files after database adoption
- add migrations only when the SQLite implementation becomes active

### Provider-Backed AI Runtime

- add provider-backed AI integrations for supported providers
- persist prompts, review findings, and evidence references in a structured
  audit trail
- keep model providers read-only with respect to ledger mutation

### Source And Output Adapter Expansion

- add real blockchain adapters under `adapters/sources/explorers/` when they
  normalize exported blockchain evidence
- add real platform API adapters under `adapters/sources/platforms/` when they
  become productized
- keep reserved entry points stubbed rather than half-implemented
- keep adapters self-contained with tests and metadata colocated

### Test Follow-Through

- keep scaffold and golden-refresh commands aligned with any future pack-layout
  move so fixture authors still have one stable toolchain
- continue moving adapter packs toward adapter-owned layout so plugin
  extraction does not require another test-tree rewrite
- expand the current split test profiles only when additional CI
  infrastructure is introduced

## Change Control

When roadmap order, architecture, schema, or rollout gates change, update all
of the following together:

- `ROADMAP.md`
- `docs/concepts/reconciliation-tax-architecture.md`
- `docs/status/migration-sequence.md`
