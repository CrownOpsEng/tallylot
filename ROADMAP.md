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
  - [`docs/reference/journal-contract.md`](docs/reference/journal-contract.md)
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
- normal product reruns are automatic, idempotent, deterministic, and
  transparent to the user
- the fast path stays on ordinary reruns from authoritative persisted truth
  rather than on manual rebuild workflows or special rerun hygiene
- hot-path calculations stay on authoritative kernels and required hot-path
  fields only; anything outside the calculation path stays in sidecars or
  other declared non-kernel detail
- when authoritative inputs change, the affected stages or partitions rerun
  automatically while unchanged partitions skip recalculation
- safe full-rebuild overrides may bypass cache or fingerprint skips only when
  they can rebuild from the declared upstream truth without losing manual
  adjustments outside the owned generated surface
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
- prefer transparent rerun-safe behavior over rebuild-style operator workflows
  when correcting downstream generated outputs
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

Phase 0 is complete. Its durable outputs live on the owner docs that carry
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

Phase 1 is complete. Its implemented runtime truth and durable references
live on the owner surfaces that describe the active bridge boundary and product
outputs:

- [Current State](docs/status/current-state.md)
- [Product Outputs](docs/workspace/working/products/README.md)
- [Evidence And Claim Contract](docs/reference/evidence-claim-contract.md)
- [CHANGELOG.md](CHANGELOG.md)

## Phase 2. `ClaimSet` Is Complete

Phase 2 is complete. Its implemented runtime truth and durable references
live on the owner surfaces that describe the active claim-stage authority and
the retained bridge compatibility boundary:

- [Current State](docs/status/current-state.md)
- [Evidence And Claim Contract](docs/reference/evidence-claim-contract.md)
- [Architecture Overview](docs/concepts/architecture-overview.md)
- [Product Outputs](docs/workspace/working/products/README.md)
- [CHANGELOG.md](CHANGELOG.md)

## Phase 3. `EconomicFacts` Is Complete

Phase 3 is complete. Its implemented runtime truth and durable references
live on the owner surfaces that describe the active downstream economics
authority and retained compatibility views:

- [Current State](docs/status/current-state.md)
- [Architecture Overview](docs/concepts/architecture-overview.md)
- [Economics Reconciliation Checkpoint Contract](docs/reference/economics-reconciliation-checkpoint-contract.md)
- [Migration Sequence](docs/status/migration-sequence.md)
- [Product Outputs](docs/workspace/working/products/README.md)
- [CHANGELOG.md](CHANGELOG.md)

## Phase 4. `ReconciliationState` Is Complete

Phase 4 is complete. Its implemented runtime truth and durable references
live on the owner surfaces that describe the active downstream reconciliation
authority and retained compatibility views:

- [Current State](docs/status/current-state.md)
- [Architecture Overview](docs/concepts/architecture-overview.md)
- [Economics Reconciliation Checkpoint Contract](docs/reference/economics-reconciliation-checkpoint-contract.md)
- [Migration Sequence](docs/status/migration-sequence.md)
- [Product Outputs](docs/workspace/working/products/README.md)
- [CHANGELOG.md](CHANGELOG.md)

## Phase 5. `Checkpoint` Is Complete

Phase 5 is complete. Its implemented runtime truth and durable references
live on the owner surfaces that describe the active downstream checkpoint
authority and retained compatibility views:

- [Current State](docs/status/current-state.md)
- [Architecture Overview](docs/concepts/architecture-overview.md)
- [Economics Reconciliation Checkpoint Contract](docs/reference/economics-reconciliation-checkpoint-contract.md)
- [Migration Sequence](docs/status/migration-sequence.md)
- [Product Outputs](docs/workspace/working/products/README.md)
- [CHANGELOG.md](CHANGELOG.md)

## Phase 5A. Accounting Boundary And Automatic Rerun Correction Is Complete

Phase 5A is complete. Its implemented runtime truth, durable contract updates,
and control-plane enforcement live on the owner surfaces that now describe the
automatic fast path and accounting boundary directly:

- [Current State](docs/status/current-state.md)
- [Operator Quickstart](docs/guides/operator-quickstart.md)
- [Source Intake](docs/guides/source-intake.md)
- [Normalize, Screen, And Stage](docs/guides/normalize-screen-stage.md)
- [Architecture Overview](docs/concepts/architecture-overview.md)
- [Domain Ontology](docs/concepts/domain-ontology.md)
- [Bridge To Target Mapping](docs/concepts/bridge-to-target-mapping.md)
- [Pipeline Stage Contracts](docs/concepts/pipeline-stage-contracts.md)
- [Reconciliation, Checkpoint, Journal, And Tax Architecture](docs/concepts/reconciliation-tax-architecture.md)
- [Evidence And Claim Contract](docs/reference/evidence-claim-contract.md)
- [Economics Reconciliation Checkpoint Contract](docs/reference/economics-reconciliation-checkpoint-contract.md)
- [Journal Contract](docs/reference/journal-contract.md)
- [Target Persistence Reference](docs/reference/target-persistence-reference.md)
- [Migration Sequence](docs/status/migration-sequence.md)
- [CHANGELOG.md](CHANGELOG.md)

## Phase 6. Land Canonical Accounting Journal

Goal:

- make canonical journal expansion, repo-owned entry checks, and backend
  handoff a first-class downstream stage

Detailed contract pages:

- [Journal Contract](docs/reference/journal-contract.md)
- [Pipeline Stage Contracts](docs/concepts/pipeline-stage-contracts.md)
- [Reconciliation, Checkpoint, Journal, And Tax Architecture](docs/concepts/reconciliation-tax-architecture.md)
- [Migration Sequence](docs/status/migration-sequence.md)

Scope boundary:

- `Journal` consumes authoritative `EconomicFacts` and `Checkpoint` kernels
  from the bounded downstream slice
- `Journal` is the canonical accounting product and write model for
  `JournalEntryRecord`, `PostingRecord`, `EntryCheckRecord`, journal-owned
  gaps, and backend-neutral journal detail
- `accounting` is the owning capability for canonical journal construction,
  accounting entry checks, backend orchestration, and bounded accounting
  inspection
- `ledger_cli` is the first accounting backend id, while `ledger-cli`
  remains a downstream corroboration and inspection tool only
- the accounting backend seam is intentionally replaceable, and backend
  invocation plus backend-specific artifacts remain derived outputs
  downstream of `Journal`
- `TaxInputs` and `TaxOutputs` keep identity and kernel meaning anchored to
  authoritative `Checkpoint` plus `EconomicFacts`; this slice does not add
  `journal_ref` or backend-derived identity to tax products

Implementation slices:

- land canonical journal expansion, repo-owned entry checks, backend
  orchestration, and backend-neutral detail generation under
  `application/accounting/`
- land `domain/accounting/` for the target accounting family
- land `ports/accounting_backends.py` for the replaceable accounting backend
  seam and `infrastructure/ledger_cli/` for the first subprocess-backed
  backend implementation
- persist the journal kernel plus backend-neutral detail at the journal root
  and keep `ledger_cli` artifacts under
  `working/products/journals/<journal_id>/backends/ledger_cli/`
- keep current compatibility renderers and fact-output adapters on their
  existing compatibility path until their own cutover slices land

Workflow scope:

- build canonical accounting journal
- inspect journal
- explain blocked entries
- validate through the selected accounting backend
- use bounded `ledger-cli` inspection commands for accounting corroboration:
  `print`, `accounts`, `balance`, and `register`

Explicitly exclude:

- broad reporting
- dashboards
- portfolio analytics
- performance analytics
- visualization datasets

Exit criteria:

- repeated runs on unchanged authoritative inputs preserve `journal_id`,
  `entry_id`, `posting_id`, and `entry_check_id`
- deterministic reruns on unchanged authoritative inputs preserve the owned
  generated outputs
- blocked entries emit explicit journal-owned checks or gaps and zero postings
  instead of silent omission
- reruns do not corrupt generated state or append stale rows
- `ledger_cli` corroboration reruns from authoritative `Journal` kernels
  alone without changing journal authority or repairing data
- later backends can replace `ledger_cli` without redefining journal ids,
  journal-owned check outcomes, or tax identity
- no ledger-derived identity leaks into tax
- no user-facing rebuild workflow or manual rerun hygiene is required to keep
  the product healthy
- detailed backend artifact, validation-lane, and cutover rules stay on the
  owner docs rather than in this planning surface

## Phase 7. Land `TaxInputs` And `TaxOutputs`

Goal:

- build policy-ready tax inputs and policy-owned outputs from accepted
  upstream products

Detailed contract pages:

- [Pipeline Stage Contracts](docs/concepts/pipeline-stage-contracts.md)
- [Journal Contract](docs/reference/journal-contract.md)
- [Reconciliation, Checkpoint, Journal, And Tax Architecture](docs/concepts/reconciliation-tax-architecture.md)
- [Migration Sequence](docs/status/migration-sequence.md)

Scope boundary:

- `TaxInputs` remain anchored to authoritative `Checkpoint` plus
  `EconomicFacts`, not to `Journal`, `journal_ref`, or any backend-generated
  artifact
- selected tax policies emit `TaxOutputs`, tax carry-forward rows, and
  explicit unsupported-input rows from those authoritative upstream products
- journal outputs and journal-backend findings may inform downstream review
  posture only as declared non-authoritative detail
- `TaxOutputs` keep grouped readiness local to the active tax-first path and do
  not become general reporting storage

Implementation slices:

- define basis-pool and basis-transition construction over accepted upstream
  truth
- partition tax work by `tax_year` and carry-forward refs rather than
  full-history rescans
- emit filing-critical policy outputs from selected policies without treating
  CoinTracking tax reports, journal backends, or renderer outputs as peer
  authorities

Exit criteria:

- `TaxInputs` and `TaxOutputs` rerun deterministically from authoritative
  `Checkpoint`, `EconomicFacts`, and selected tax-policy inputs without
  bridge facts, `journal_ref`, or backend-derived identity
- `2023` to `2025` outputs can be produced from reconciled economics and
  accepted checkpoint truth without treating CoinTracking tax reports as the
  ledger
- `TaxOutputs` remains a narrow tax-output exception rather than the permanent
  home of general reporting, dashboards, portfolio views, performance
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
  `application/portfolio/`, `application/performance/`,
  `application/reporting/`, and `application/investigation/`

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
- derived snapshots and reusable state should be introduced where rerun cost
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
- add deterministic rerun coverage for target kernels and compatibility views
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
