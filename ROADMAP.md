# ROADMAP

This file is the forward planning document for the repo.

- Completed work belongs in [CHANGELOG.md](CHANGELOG.md).
- The currently implemented runtime surface belongs in
  [`docs/status/current-state.md`](docs/status/current-state.md).
- Detailed contract ownership lives in:
  - [`docs/concepts/current-bridge-contracts.md`](docs/concepts/current-bridge-contracts.md)
  - [`docs/concepts/bridge-to-target-mapping.md`](docs/concepts/bridge-to-target-mapping.md)
  - [`docs/concepts/pipeline-stage-contracts.md`](docs/concepts/pipeline-stage-contracts.md)
  - [`docs/reference/first-slice-contract.md`](docs/reference/first-slice-contract.md)
  - [`docs/concepts/domain-ontology.md`](docs/concepts/domain-ontology.md)
  - [`docs/concepts/gaps-and-readiness.md`](docs/concepts/gaps-and-readiness.md)
  - [`docs/concepts/reconciliation-tax-architecture.md`](docs/concepts/reconciliation-tax-architecture.md)
  - [`docs/status/migration-sequence.md`](docs/status/migration-sequence.md)

This roadmap tracks the implementation program from the current bridge toward
the target stage-first architecture. The current bridge remains the live runtime
seam, but it is not the long-term architecture center.

## Planning Anchors

These anchors drive sequencing and acceptance criteria:

- the historical CoinTracking export boundary around `2023-08-05` remains an
  oracle boundary, not a trusted opening checkpoint
- the first source-backed checkpoint target remains near `2026-03-23`
- the filing-critical output horizon remains `2023` through `2025`
- reconciliation remains the trust gate before checkpoint adoption, accounting,
  and tax
- checkpoint truth is accepted state with explicit acceptance basis
- capture identity is metadata, not path
- typed provenance stays a runtime model and is flattened only when writing
  artifacts
- normalization is capture-scoped and reconciliation is source-assembly-scoped
- raw-evidence derivation is the supported semantic parity path
- current bridge names remain current-state truth until later implementation
  slices replace them

## Transition Rules

- preserve current working behavior while new foundations land
- avoid freezing the current bridge as the long-term architecture center
- keep adapters and services shippable at every checkpoint
- keep CoinTracking as one edge projection and oracle family, not a migration
  anchor
- preserve current bridge truth while establishing the target stage and
  ontology ownership model
- do not rename live bridge symbols or the live repo-only support package as a
  docs-only side effect; land those as later implementation slices

## Cross-Cutting Foundations

These are blocking shared foundations for later implementation work:

- the live bridge contracts documented in
  [`docs/concepts/current-bridge-contracts.md`](docs/concepts/current-bridge-contracts.md)
- the bridge-to-target transformation rules documented in
  [`docs/concepts/bridge-to-target-mapping.md`](docs/concepts/bridge-to-target-mapping.md)
- the target stage contracts documented in
  [`docs/concepts/pipeline-stage-contracts.md`](docs/concepts/pipeline-stage-contracts.md)
- the bounded first-slice parity and replay contract documented in
  [`docs/reference/first-slice-contract.md`](docs/reference/first-slice-contract.md)
- the target ontology and identity seams documented in
  [`docs/concepts/domain-ontology.md`](docs/concepts/domain-ontology.md)
- the shared gap, readiness, and `SubjectRef` rules documented in
  [`docs/concepts/gaps-and-readiness.md`](docs/concepts/gaps-and-readiness.md)
- bridge-only classification rules documented in
  [`docs/concepts/transaction-classification.md`](docs/concepts/transaction-classification.md)
- oracle boundary rules documented in
  [`docs/concepts/oracle-boundaries.md`](docs/concepts/oracle-boundaries.md)
- repo-only support boundary direction: the current live package remains
  `repo_support/`, while later implementation should rename and split that
  dev-only surface under `dev_support/`

Rules:

- do not let new stages invent their own blocker or readiness surface
- do not let new work recentre the architecture on the current bridge types
- do not turn repo-only support into a permanent generic catch-all under the
  current live `repo_support/` name
- do not rename live bridge symbols or the live repo-only support package as a
  docs-only side effect; land those as later implementation slices

Shared-foundation deliverables before broad pipeline expansion:

- one typed provenance family across evidence, claims, balances, gaps,
  readiness, checkpoints, accounting, and tax artifacts
- one target-product versioning, compatibility, canonical-serialization, and
  fingerprint rule
- one controlled gap taxonomy with stage ownership, blocking scope,
  `SubjectRef`, candidate interpretations, required evidence, and allowed
  resolution methods
- one gap-attachment rule that covers subject, group, and dataset scopes
- one readiness vocabulary reused across all stages
- one subject-first readiness model with derived projections rather than one
  mandatory global readiness cube
- one kernel-and-envelope rule with stable rehydration joins
- one explicit identity seam for instrument, contract, position, location,
  legal owner, beneficial owner, and counterparty identity
- one minimum `ClaimSet` taxonomy shared across adapters and later compilation
- one minimum `EconomicFacts` invariant grammar
- one typed tax-policy selection seam reused by later `TaxInputs` and
  `TaxOutputs` work
- one minimum `TaxInputs` determinant grammar
- one checkpoint assertion vocabulary reused by reconciliation, checkpoint
  adoption, accounting, and tax
- one checkpoint acceptance vocabulary for trust level, acceptance basis,
  evidence class, continuity proof, and minimum admissibility rules
- one canonical bridge-to-target mapping for how current planner and
  translation seams become the first proto-`EvidenceSet` and proto-`ClaimSet`
  slices
- one named first vertical slice with parity and replay gates

Exit criteria:

- shared gap and readiness models exist with typed reducers and artifact
  contracts
- every new stage can emit stage-owned gaps without inventing one-off issue
  formats
- dataset summaries derive from subject-level readiness instead of hand-built
  status prose
- target products have owned versioning and fingerprint rules
- the canonical bridge-to-target mapping is published and linked as the single
  authority
- per-product kernel, id, serialization, fingerprint, and adjudication rules
  are frozen on the target owner page
- `CheckpointAssertion`, issue-to-gap mapping, and review-sidecar rules are
  defined on their owning pages
- the first vertical slice and its bridge-to-target landing path are explicit
- broad target package scaffolding does not begin before these contracts are
  frozen

## MVP Scope Guardrails

- use the current bridge until the next concrete slice needs a richer stage
  contract
- do not wait for every target product to exist before improving the active
  filing path
- add new stage models, reducers, or ports only when one bounded slice needs
  them for correctness, determinism, or later-stage reuse
- avoid plugin systems, manifest families, or broad orchestration abstractions
  before a second concrete implementation requires them
- keep unsupported or deferred behavior explicit through blockers instead of
  low-confidence partial support
- prefer one end-to-end vertical slice that proves a new stage over several
  horizontal framework layers with no proven consumer
- default first vertical slice: the planner-enabled Coinbase retail export
  family plus statement-backed balance observation flow, unless the active
  filing workspace requires another Tier A family to land first
- the repo default first slice is the bounded contract in
  [`docs/reference/first-slice-contract.md`](docs/reference/first-slice-contract.md);
  it is not a claim that the actual `2023` to `2025` filing adapter inventory
  is already known in-repo
- keep crypto filing-critical coverage primary for the MVP while using generic
  runtime names and boundaries that can later absorb other instrument classes
- keep filing-critical adapter stabilization distinct from broad family
  migration, while allowing unified adapter contract and bridge-mapping work in
  Phase 0 when it removes first-slice drift

## Performance Expectations

Rollout choices must preserve bounded recalculation cost.

Rules:

- expensive reducers must be partitionable by the dimensions the owning stage
  actually uses, with derived reporting projections added only where needed
- hot-path calculations should operate on compact typed records instead of
  repeatedly joining provenance, review, or renderer payloads
- derived snapshots and reusable state should be introduced where replay cost
  becomes material
- tax work should support tax-year partitioning and carry-forward reuse instead
  of recomputing full acquisition history for every output row

## Implementation Program

### Phase 0. Shared Foundations, Contract Lock, And First-Slice Prep

Goal:

- finish the shared architecture, naming, support-model, and control-plane
  baseline before broad implementation slices land
- freeze the contracts that the first implementation slice must rely on instead
  of leaving them to stage-local interpretation

Deliver:

- focused ownership docs for the current bridge, target stage contracts,
  ontology, and gap/readiness contracts
- aligned roadmap, migration, and architecture anchors
- target `dev_support/` direction documented while current `repo_support/`
  remains truth in current-state text
- explicit trust-gate ownership for reconciliation, checkpoints, accounting,
  and tax
- target-product versioning, serialization, and fingerprint rules
- kernel-and-envelope rules with stable rehydration joins
- shared gap scope, `SubjectRef`, and evidence-readiness rules
- minimum `ClaimSet`, `EconomicFacts`, `Checkpoint`, and `TaxInputs`
  vocabularies
- one canonical bridge-to-target mapping for how current planner and
  translation seams land the first proto-`EvidenceSet` and proto-`ClaimSet`
  slices
- unified adapter product and facet prep where it removes first-slice drift,
  without broad family migration or wrapper lanes
- one named first vertical slice with parity and replay gates

Exit criteria:

- a contributor can identify what is current, what is target, who owns each
  contract, and what the next slice should land without reading the same
  definition in several conflicting places
- the first slice does not depend on an implicit adapter rewrite that is not
  written down
- the first slice does not depend on inventing ids, ordering, serialization,
  fingerprints, replay checks, or allowed drift at implementation time
- broad implementation can start without each stage inventing its own meaning
  for gaps, claims, checkpoint acceptance, or fingerprints
- broad implementation does not start with target package scaffolding that
  outruns the frozen contract set

### Phase 1. Formalize `EvidenceSet`

Goal:

- make deterministic evidence selection and source-local observation capture
  the formal first pipeline product

Deliver:

- deterministic evidence selection reports
- explicit selected, superseded, and blocked evidence outputs
- source-local parsed observation contracts
- evidence provenance and locator guarantees aligned with the target contract
- evidence summary and issue surfaces that remain source-local rather than
  prematurely economic
- a bridge landing path from planner-owned artifacts into proto-`EvidenceSet`
  without requiring broad unified-adapter migration first

Exit criteria:

- the runtime can explain why every selected source artifact won and why every
  superseded artifact lost
- source-local observations survive beyond file-selection time

### Phase 2. Introduce `ClaimSet`

Goal:

- interpose a real claim layer between evidence selection and final economic
  truth

Deliver:

- claim-native contracts for activity, balance, ownership, location,
  instrument, contract, and valuation meaning
- claim-owned issues and reviews
- explicit handling for materially unresolved meaning
- bridge loosening so ambiguous rows can remain claims without being forced
  into final bridge semantics
- at least one ambiguous row family that survives as a claim rather than being
  coerced into a guessed final fact
- a bounded adapter-family path that can emit claim-native outputs without
  making the full unified adapter migration a hidden prerequisite

Exit criteria:

- at least one adapter family emits claim-native outputs before economic
  compilation
- ambiguous source rows can remain claim-complete but economically unresolved

### Phase 3. Land `EconomicFacts`

Goal:

- move from bridge-first fact shaping toward the target economic layer while
  preserving parity

Deliver:

- claim-to-economic compilation seam
- target-directed economic models aligned to the target ontology
- explicit preservation of settlement, lifecycle, valuation, and identity seams
- bridge retirement rules for the slices that no longer need
  `EconomicActivityDraft` or `TransactionFact`
- parity coverage for the first claim-to-economic vertical slice

Exit criteria:

- accepted economic meaning is no longer constrained by bridge activity labels
- at least one bounded slice proves target economic modeling without wrapper
  lanes

### Phase 4. Land `ReconciliationState`

Goal:

- move continuity, linkage, completeness, and checkpoint candidacy onto an
  explicit reconciliation product

Deliver:

- transfer links, balance targets, continuity, and checkpoint candidacy under
  `ReconciliationState`
- target gap and readiness models where the owning stage can support them
- corroboration sidecars and deterministic correction handling
- independence from raw capture layout and bridge-only balance assumptions

Exit criteria:

- reconciliation is expressed as explicit completeness and continuity decisions
- exact balance assertions are one reconciliation surface, not the whole
  reconciliation product

### Phase 5. Land `Checkpoint`

Goal:

- make accepted checkpoint truth and acceptance basis explicit

Deliver:

- accepted checkpoint assertions under `Checkpoint`
- source-backed checkpoint evidence requirements
- trust level and acceptance basis
- intentional opening-state adoption with provenance
- manual balance submission as typed checkpoint-owned input

Exit criteria:

- checkpoint truth is explicit accepted state, not an inferred side effect

### Phase 6. Land `Journal`

Goal:

- make accounting expansion and validation a first-class downstream stage

Deliver:

- internal journal model
- posting expansion and validation surfaces
- accounting-owned blockers
- renderer orchestration over accepted truth

Exit criteria:

- accounting validates accepted truth without acting as a truth repair layer

### Phase 7. Land `TaxInputs` And `TaxOutputs`

Goal:

- build policy-ready tax determinants and policy-owned outputs from accepted
  truth

Deliver:

- `TaxInputs` contracts
- tax-policy selection seam
- first filing-critical policy implementation
- Canada MVP policy
- year partitioning, carry-forward state, and explicit tax-owned blockers
- `TaxOutputs` derived only from selected tax policies over `TaxInputs`

Exit criteria:

- `2023` to `2025` outputs can be produced from reconciled economics plus
  accepted checkpoint truth without CoinTracking tax reports

### Phase 8. Repo-Only Support Reset

Goal:

- rename and split the dev-only shared support surface cleanly

Deliver:

- rename `repo_support/` to `dev_support/`
- split repo-only support by owned seam such as `quality/`,
  `review_verification/`, `typecheck/`, `fixtures/`, and environment/path
  helpers
- update control-plane automation, docs, and tests to the new dev-only
  boundary

Exit criteria:

- repo-only support has an explicit dev-only boundary name
- shared repo-only support no longer reads like a generic support sink

### Phase 9. Public Repo And Agent Hardening

Goal:

- finish the post-filing documentation and repository hardening needed for a
  public, agent-usable codebase

Deliver:

- publishable fixtures and provenance-safe docs
- delivery guardrails layered across platform settings, repo-native
  validators, and agent defaults
- control-plane ownership routing and default-branch guardrail audits
- repo-native PR review routing and change-sensitive PR-only review checks
- benchmark-backed quality-gate scheduling and explicit CI job splits instead
  of one opaque parity shell

Exit criteria:

- repo-safe fixtures and documentation are maintained without private workflow
  assumptions
- a new contributor or coding agent can find the correct roadmap, status,
  concept, guide, and workspace docs without broad context loading
- the default-branch delivery path is enforced strongly enough that a single
  agent mistake cannot silently bypass the intended PR-only workflow
- the repo can audit local CODEOWNERS coverage and live GitHub delivery
  settings together without broad context loading or one-off shell repair work

### Phase 10. Post-Core Runtime Expansion

Goal:

- expand runtime surfaces only after the filing-critical core is stable

Deliver:

- thin HTTP or agent-facing interfaces over the same typed application
  contracts
- SQLite-backed active storage behind repository ports
- provider-backed AI implementations with explicit audit trails
- additional productized source and output adapters beyond the current
  high-value evidence sources

Exit criteria:

- post-core expansion layers on top of the filing-capable runtime instead of
  destabilizing it

## Guardrails

- keep the active filing path moving while the architecture becomes more
  explicit
- prefer one end-to-end vertical slice that proves a new stage over horizontal
  framework buildout with no proven consumer
- keep unsupported or deferred behavior explicit through blockers instead of
  low-confidence partial support
- do not reintroduce wrapper lanes, migration shims, or dual active runtime
  models once a bounded replacement is ready
- when work affects architecture, schema, or sequencing, update this file
  together with the owning concept and migration docs

## Cross-Cutting Workstreams

These workstreams continue across the major phases above.

### Oracle Lane

- keep CoinTracking report readers and comparison tooling under `tools/oracles/`
- use oracle artifacts for regression, black-box comparison, and historical
  review only
- never let oracle files become hidden production dependencies

### Adapter Completion

- complete parity coverage for supported source adapters on the bridge and then
  on target-stage products as slices land
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
- add journal validation coverage
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
- journal validation passes for supported activity
- the forward-computed state from the `2023-08-05` oracle boundary lands on the
  source-backed checkpoint
- `2023`, `2024`, and `2025` outputs can be reproduced from workspace evidence

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
- validation parse-and-balance coverage
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
- introduce target stage products before expanding downstream policy services
- replace bridge-era or older transitional artifacts directly while migrating
  downstream services
- remove superseded transition-first workflows once replacement consumers land

Do not:

- add SQLite first
- add a web UI
- add generic workflow engines
- re-centralize business rules in adapters
- keep pushing new semantics into one `category` string or equivalent activity
  label sink

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

## Time Summary

AI-assisted estimate for the filing-critical path:

- `106` to `164` hours

AI-assisted estimate including open-source hardening:

- `126` to `196` hours

Those ranges assume focused implementation with the current repo standards,
tests, and documentation discipline preserved.
