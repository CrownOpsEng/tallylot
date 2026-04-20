# ROADMAP

This file is the forward planning document for the repo.

- Completed work belongs in [CHANGELOG.md](CHANGELOG.md).
- The currently implemented runtime surface belongs in
  [`docs/status/current-state.md`](docs/status/current-state.md).
- Detailed contract pages live in:
  - [`docs/concepts/current-bridge-contracts.md`](docs/concepts/current-bridge-contracts.md)
  - [`docs/concepts/bridge-to-target-mapping.md`](docs/concepts/bridge-to-target-mapping.md)
  - [`docs/concepts/pipeline-stage-contracts.md`](docs/concepts/pipeline-stage-contracts.md)
  - [`docs/concepts/domain-ontology.md`](docs/concepts/domain-ontology.md)
  - [`docs/concepts/gaps-and-reviews.md`](docs/concepts/gaps-and-reviews.md)
  - [`docs/concepts/reconciliation-tax-architecture.md`](docs/concepts/reconciliation-tax-architecture.md)
  - [`docs/reference/evidence-claim-contract.md`](docs/reference/evidence-claim-contract.md)
  - [`docs/reference/economics-reconciliation-checkpoint-contract.md`](docs/reference/economics-reconciliation-checkpoint-contract.md)
  - [`docs/status/migration-sequence.md`](docs/status/migration-sequence.md)

This roadmap tracks the implementation program from the current bridge toward
the target runtime pipeline. The current bridge remains the live runtime seam
until later slices replace it, but it is not the long-term architecture center.

**Current runtime note:** CoinTracking references in this roadmap describe the
current adapter-edge and oracle-comparison boundaries, not canonical target
naming.

**Exception rationale:** `assessment/` stays in this roadmap only as the shared
contract and sidecar root for the nested `gap/` and `review/` families. It is
not a generic application center.

## Planning Anchors

These anchors drive sequencing and acceptance criteria:

- reconciliation remains the trust gate before checkpoint adoption, journal
  emission, and tax
- accepted checkpoint truth has explicit acceptance basis
- primary evidence and evidence-backed checkpoints remain first-class
- raw-evidence derivation is the supported meaning-parity path
- capture identity is `capture_uid`, not path
- typed provenance stays a runtime model and is flattened only at file and
  export boundaries
- normalization is capture-scoped and reconciliation is source-assembly-scoped
- current bridge names remain current-state truth until later implementation
  slices replace them
- CoinTracking remains an edge adapter and oracle surface, not the runtime
  ledger model
- broader grouped and query surfaces remain deferred until the trigger ladder
  below fires
- filing-critical `TaxOutputs` and narrow rendering outputs may keep derived
  grouped output logic only for the active tax-first window

## Transition Rules

- preserve current working behavior while new foundations land
- avoid freezing the current bridge as the long-term architecture center
- keep adapters and services shippable at every checkpoint
- preserve current bridge truth while establishing target product ownership
- do not let bridge compatibility views become a second architecture
  center
- do not let shared grouped readiness or shared application assessment behavior
  harden into the long-term architecture
- keep broader derived read models and projections deferred until the trigger
  ladder fires, then activate them as capability-owned application surfaces
- do not rename live bridge symbols or repo-only support packages as a docs-only
  side effect
- freeze short-first canonical stable ids, catalog-declared owner-local short
  slots, and deterministic boundary checks that require local slots only on
  declared owner-local surfaces and canonical ids everywhere else

## Phase 0. Contract Lock And Bounded-Slice Prep

Phase 0 is complete. Its durable outputs now live on the owner docs that carry
ongoing contracts and migration rules:

- [Bridge To Target Mapping](docs/concepts/bridge-to-target-mapping.md)
- [Pipeline Stage Contracts](docs/concepts/pipeline-stage-contracts.md)
- [Domain Ontology](docs/concepts/domain-ontology.md)
- [Gap, Review, And Shared Attachment](docs/concepts/gaps-and-reviews.md)
- [Reconciliation, Checkpoint, Journal, And Tax Architecture](docs/concepts/reconciliation-tax-architecture.md)
- [Evidence And Claim Contract](docs/reference/evidence-claim-contract.md)
- [Economics Reconciliation Checkpoint Contract](docs/reference/economics-reconciliation-checkpoint-contract.md)
- [Migration Sequence](docs/status/migration-sequence.md)
- [CHANGELOG.md](CHANGELOG.md)

Keep detailed completion proof, gate tables, and durable contract semantics on
those owner docs rather than restating them here.

## Phase 1. `EvidenceSet` Is Complete

Phase 1 is complete. Its implemented runtime truth and durable references now
live on the owner surfaces that describe the active bridge boundary and product
outputs:

- [Current State](docs/status/current-state.md)
- [Product Outputs](docs/workspace/working/products/README.md)
- [Evidence And Claim Contract](docs/reference/evidence-claim-contract.md)
- [CHANGELOG.md](CHANGELOG.md)

## Phase 2. Land `ClaimSet`

Goal:

- interpose a real claim stage between evidence capture and final economic
  truth

Deliver:

- evidence-local `ClaimSet` emission keyed by `claim_set_id`
- explicit claim scopes, mutually exclusive claim bundles, and
  claim-bundle-decision records
- claim fields frozen for the first upstream slice plus
  `observation_refs`
- shared gap and review outputs attached to claim scopes where needed, with any
  readiness views staying local to the claim-owning capability
- declared compatibility views for `EconomicActivityDraft` and
  `SourceTranslationBatch`, with legacy hint fields kept outside `ClaimSet`
  kernels

Exit criteria:

- ambiguous source meaning can remain explicit without being forced into final
  economic meaning
- claim-bundle decisions remain claim-owned and do not carry economic
  truth

Transition to Phase 3:

- downstream bridge outputs stay on the live bridge path until
  `EconomicFacts` exists
- the first downstream slice is the first slice that turns those downstream
  bridge outputs into target-derived compatibility views

## Phase 3. Land `EconomicFacts`

Goal:

- move accepted economic meaning off the bridge fact path and onto the target
  economics layer

Deliver:

- `EconomicFacts` kernels keyed by `economic_facts_id` over ordered
  `claim_set_refs`
- `EconomicEventRecord`, `EconomicLegRecord`, and `ValuationRecord`
- claim-bundle-derived event identity
- bridge compatibility view for `TransactionFact`
- parity coverage for the first claim-to-economics slice

Exit criteria:

- accepted economic meaning is no longer constrained by bridge activity labels
- at least one bounded slice proves target economic modeling without wrapper
  lanes

## Phase 4. Land `ReconciliationState`

Goal:

- move continuity, linkage, completeness, and checkpoint proposal records onto an
  explicit reconciliation product

Deliver:

- `ContinuitySegmentRecord`, `BalanceTargetRecord`, and
  `CheckpointProposalRecord` for the first downstream slice
- `EventLinkRecord` when a later in-phase reconciliation increment needs
  explicit event linkage rather than inferred continuity alone
- direct `AssertionValue` fields for expected and observed balance meaning
- fixed subject and position identity seams for in-scope reconciliation
- bridge compatibility view for `balance_snapshots.csv`

Exit criteria:

- reconciliation is expressed as explicit continuity and completeness decisions
- exact balance assertions are one reconciliation concern, not the whole
  product

## Phase 5. Land `Checkpoint`

Goal:

- make accepted checkpoint truth and acceptance basis explicit

Deliver:

- `CheckpointRecord` and `CheckpointAssertionRecord`
- explicit trust level, acceptance basis, support kind, and continuity kind
- direct `AssertionValue` accepted truth
- bridge compatibility view for `balance_references.csv`

Exit criteria:

- accepted checkpoint truth is explicit, not an inferred side effect
- statement-backed checkpoint acceptance is separated cleanly from manual-only
  runtime aids

Phases 6 and later remain intentionally high-level in this round. This roadmap
repair makes Phase 0 to Phase 5 implementation decision-complete without
defining bounded slices for later downstream products yet.

## Phase 6. Land `Journal`

Goal:

- make journal expansion and entry checks a first-class downstream stage

Deliver:

- `JournalEntryRecord`, `PostingRecord`, and `EntryCheckRecord`
- journal-owned blockers and entry-check rules
- rendering orchestration over accepted upstream products that stays narrow and
  downstream-facing

Exit criteria:

- `Journal` runs entry checks over accepted truth without becoming a
  truth-repair layer

## Phase 7. Land `TaxInputs` And `TaxOutputs`

Goal:

- build policy-ready tax inputs and policy-owned outputs from accepted
  upstream products

Deliver:

- `TaxInputs` contracts
- selected tax-policy execution over those inputs
- year partitioning and tax carry-forward records
- explicit tax unsupported-input records where policy execution cannot proceed
- filing-critical policy outputs derived from accepted upstream products rather
  than CoinTracking tax reports
- `TaxOutputs` ownership of `policy_summary`, `supporting_schedule`,
  `filing_form`, policy explanations, limitations, and rendered policy content
  for the tax-first path

Exit criteria:

- `2023` to `2025` outputs can be produced from reconciled economics and
  accepted checkpoint truth without treating CoinTracking tax reports as the
  ledger
- `TaxOutputs` remains a narrow tax-output exception rather than the permanent
  home of general reporting, dashboards, portfolio views, visualization
  datasets, or investigation workflows

## Phase 8. Repo-Only Support Reset

Goal:

- rename and split the dev-only repo-support boundary cleanly

Deliver:

- rename `repo_support/` to `dev_support/`
- split repo-only support by owned seam
- update control-plane automation, docs, and tests to the new dev-only
  boundary

Exit criteria:

- repo-only support has an explicit dev-only boundary name
- shared repo-only support no longer reads like a generic sink

## Phase 9. Public Repo And Agent Hardening

Goal:

- finish the post-filing documentation and repository hardening needed for a
  public, agent-usable codebase

Deliver:

- publishable fixtures and provenance-safe docs
- delivery guardrails layered across platform settings, repo-native
  validators, and agent defaults
- control-plane ownership routing and docs-maintenance alignment for repo-safe
  execution guidance
- repo-native PR review routing and change-sensitive review checks
- benchmark-backed quality-gate scheduling and explicit CI job splits instead
  of one opaque parity shell

Exit criteria:

- a new contributor or coding agent can find the correct roadmap, status,
  concept, guide, and workspace docs without broad context loading
- the repo can audit local CODEOWNERS coverage and live GitHub delivery
  settings together without broad context loading
- the default-branch delivery path is enforced strongly enough that one mistake
  does not silently bypass the intended PR-only workflow

## Phase 10. Post-Filing Runtime Expansion

Goal:

- expand runtime surfaces only after the filing-critical runtime is stable

Deliver:

- thin HTTP or agent-facing interfaces over the same typed application
  contracts
- alternate storage backends behind repository ports
- provider-backed AI implementations with explicit audit trails
- additional productized source and output adapters beyond the current
  high-value evidence sources
- broader capability-owned derived read models and projections if no earlier
  trigger already activated them
- reserved package families stay explicit when they are finally needed:
  `application/reporting/`, `application/portfolio/`,
  `application/visualization/`, and `application/investigation/`

Exit criteria:

- post-filing expansion layers on top of the filing-capable runtime instead of
  destabilizing it

## MVP Guardrails

- use the current bridge until the next concrete slice needs a richer target
  contract
- do not wait for every later product to exist before improving the active
  filing path
- add new stage models, reducers, or ports only when one bounded slice needs
  them for correctness, determinism, or later-stage reuse
- avoid plugin systems, manifest families, or broad orchestration abstractions
  before a second concrete implementation requires them
- keep unsupported or deferred behavior explicit through blockers instead of
  low-confidence partial support
- prefer one end-to-end vertical slice that proves a new stage over several
  horizontal framework layers with no proven consumer

## Performance Expectations

Rollout choices must preserve bounded recalculation cost.

Rules:

- expensive reducers must be partitionable by the dimensions the owning stage
  actually uses
- hot-path calculations should operate on compact kernel records instead of
  repeatedly joining provenance, review, or renderer detail
- derived snapshots and reusable state should be introduced where replay cost
  becomes material
- tax work should support tax-year partitioning and tax carry-forward record reuse instead
  of recomputing full acquisition history for every output row

## Guardrails

- keep the active filing path moving while the architecture becomes more
  explicit
- keep unsupported or deferred behavior explicit through blockers instead of
  low-confidence partial support
- keep derived grouped outputs inside `application/tax/`,
  `application/rendering/`, or compatibility views only while they remain
  exclusive to the tax-first path
- do not reintroduce wrapper lanes, migration shims, or dual active runtime
  models once a bounded replacement is ready
- when work affects architecture, schema, or sequencing, update this file
  together with the owning concept and migration docs

## Cross-Cutting Workstreams

### Oracle Lane

- keep CoinTracking report readers and comparison tooling under `tools/oracles/`
- use oracle comparison packages for regression, black-box comparison, and
  historical review only
- never let oracle packages or files become hidden production dependencies

### Adapter Completion

- complete parity coverage for supported source adapters on the bridge and then
  on target-stage products as slices land
- tighten overlap heuristics, duplicate detection, and file-family signatures
  where capture ownership remains ambiguous
- extend shared adapter support only where it removes repeated adapter-local
  workflow code

### Verification And Tests

- maintain parser and adapter contract tests
- expand compatibility-view parity tests
- add replay coverage for target kernels and compatibility views
- add reconciliation parity and checkpoint continuity tests
- add journal entry-check coverage
- add tax policy coverage with explicit tax unsupported-input records
- keep end-to-end smoke workflows for each major slice before removing older
  transition paths

### Test Preservation

- no test deletions without explicit human approval
- no silent assertion removal
- no fixture simplification that hides previous edge-case coverage
- test relocation or renaming is acceptable only when behavior coverage is
  preserved or improved
- every refactor slice that changes tests must state what old behavior was
  covered, where it is covered now, and whether coverage became stronger,
  weaker, or simply moved
