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
  - [`docs/concepts/gaps-and-readiness.md`](docs/concepts/gaps-and-readiness.md)
  - [`docs/concepts/reconciliation-tax-architecture.md`](docs/concepts/reconciliation-tax-architecture.md)
  - [`docs/reference/first-upstream-slice-contract.md`](docs/reference/first-upstream-slice-contract.md)
  - [`docs/reference/first-downstream-slice-contract.md`](docs/reference/first-downstream-slice-contract.md)
  - [`docs/status/migration-sequence.md`](docs/status/migration-sequence.md)

This roadmap tracks the implementation program from the current bridge toward
the target runtime pipeline. The current bridge remains the live runtime seam
until later slices replace it, but it is not the long-term architecture center.

**Current runtime note:** CoinTracking references in this roadmap describe the
current adapter-edge and oracle-comparison boundaries, not canonical target
naming.

**Exception rationale:** `assessment/` stays in this roadmap only as the shared
root for the nested `gap/`, `review/`, and `readiness/` families. It is not a
generic assessment bucket.

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

## Transition Rules

- preserve current working behavior while new foundations land
- avoid freezing the current bridge as the long-term architecture center
- keep adapters and services shippable at every checkpoint
- preserve current bridge truth while establishing target product ownership
- do not let bridge compatibility views become a second architecture
  center
- do not rename live bridge symbols or repo-only support packages as a docs-only
  side effect

## Phase 0. Contract Lock And Bounded-Slice Prep

Goal:

- freeze the contract pages that bounded implementation slices need
- remove architecture ambiguity before broad implementation begins

Broad implementation must not begin until the contract pages freeze these
contracts.

Must freeze:

- `EvidenceSet` record families, ids, cardinality, and intentional
  `selection_fingerprint` identity churn
- critical-path `EvidenceObservationRecord` field tables for
  `statement_document` and `statement_balance_row`
- `ClaimSet` claim-scope, claim-bundle, and claim-bundle-decision model
- critical-path `ClaimRecord` field tables, `observation_refs`, and
  the compatibility sidecar boundary for retained legacy hint fields
- `AssertionValue`, `PositionRef`, and `ContractRef`
- shared gap, review, and readiness records and sidecars:
  `GapRecord`, `GapExplanation`, `ReviewRecord`,
  `ReviewExplanation`, `ReadinessRecord`, `ReadinessRollupRecord`,
  `SubjectRef = [subject_kind, subject_key]`, truthful `claim_scope_id` and `balance_target_id`
  attachments, and the downstream shared-subject seams needed for journal
  and tax records
- product ids, upstream product-ref multiplicity, and the rule that product
  refs use product ids rather than `kernel_scope_id`
- target naming rules that distinguish concepts, refs, ids, records,
  views, rollups, reports, and sidecars without baking bridge-era
  qualifiers or source-specific crypto nouns into shared target names, and
  that keep stage-local ids explicit once they cross into downstream products,
  keep stage-owned helper-ref families mirrored across sibling refs,
  keep product-id component order aligned to product-header order, keep
  canonical readiness rollups stage- and domain-oriented, use target-owned
  label pairs such as `location_group_label` and `location_label` when
  preserving source-provided location labels, keep generic downstream record
  families stage-owned with names such as `TaxCarryForwardRecord` and
  `TaxUnsupportedInputRecord`, keep partition-scope labels aligned to the
  actual identity dimensions they reduce over, describe non-authoritative
  bridge outputs as derived compatibility views rather than bridge-era
  compile steps, and prefer direct kind values such as `instrument` over
  pseudo-type labels
- child-id and helper-ref naming that freezes `claim_bundle_decision_id`,
  `checkpoint_proposal_id`, `JournalAccountRef`, and `JournalUnitRef` as the
  canonical downstream stems instead of shorter or mixed-family alternates
- claim-bundle decision naming that keeps `outcome` on the posture axis and
  freezes `ClaimBundleDecisionRecord.basis` to reason-only values such as
  `single_bundle`, `insufficient_identity`, `insufficient_temporal_precision`,
  `conflicting_claims`, `upstream_gap`, `policy_decision_required`, and
  `later_bundle_selected`
- balance-target naming that splits observation presence from comparison
  outcome instead of overloading one status field
- checkpoint-proposal naming that keeps proposal posture on `status` and models
  supersession separately through `superseding_proposal_ref`
- checkpoint-assertion kind naming that keeps quantity, amount, and state
  stems parallel across sibling values such as `position_quantity`,
  `cash_amount`, `basis_amount`, `owner_state`, and `location_state`
- checkpoint acceptance vocabulary that keeps `basis`, `support_shape`, and
  `continuity_kind` on distinct semantic axes, using reason labels such as
  `document_support`, `reported_support`, `manual_support`, and
  `reconciled_continuity`, observation-shape labels such as
  `document_observation`, `reported_observation`, and `manual_assertion`, and
  continuity-shape labels such as `observed_continuity`,
  `reconciled_rollforward`, `opening_rollforward`, and
  `partial_rollforward`
- package-root naming that keeps `journal` aligned across stage vocabulary and
  package ownership, keeps `economics` aligned across stage vocabulary,
  package ownership, and stage prose, uses singular concept roots such as
  `assertion/`, avoids umbrella roots such as `entities/` when the identity
  families are already known, keeps gap/review/readiness roots explicit when
  the docs mean those families directly, and keeps the shared `assessment/` root
  split into concrete nested families
  such as `gap/`, `review/`, and `readiness/`
- authoritative persistence model, product-owned directory stems, partition
  scopes, sidecar rules, and default filesystem placement
- migration authority rules, compatibility views, reader cutovers, and
  retirement gates
- package ownership and layer placement for shared functionality
- catalog-first target naming governance with one machine-readable naming
  authority, exact title expectations for enforced forward-looking docs, full
  canonical record-family coverage, and a blocking `target-naming` check on
  enforced forward-looking docs
- explicit no-invention rules for non-critical observation and claim kinds
- no placeholder valuation-measure field family until a real shared taxonomy
  exists

Deliver:

- aligned contract pages for target products, ontology, gap/review/readiness
  records and sidecars, and
  persistence rules
- explicit cutover matrix for bridge-to-target migration
- one first upstream slice and one first downstream slice
- explicit package ownership for `domain/` and `application/`
- explicit fast-path rule that reducers read kernels, not explanation sidecars
- frozen critical-path field tables and product-id rules that later writing
  work can merge without deciding new structure

Exit criteria:

- no owner concept is defined in two competing places
- no target product references an undefined record family or ref type
- no cross-stage support record or sidecar masquerades as a claim kind
- claim-stage blockers can attach to `claim_scope_id` before subject
  identity resolves, and later-stage blockers can attach to truthful
  journal or tax subjects without collapsing to kernel-scope attachment only
- no target id or helper id bakes bridge-era naming into target identity
- no canonical target contract keeps source-specific crypto nouns such as
  `wallet` when a repo-owned domain noun already owns that seam
- no bridge surface is left without an authority and retirement rule
- no hot-path field points to an undefined value ref or sidecar
- every critical-path observation and claim kind has one authoritative kernel
  field table
- no target product ref in a product header uses `kernel_scope_id` where a
  product id
  exists
- non-critical observation and claim kinds are explicitly deferred rather
  than left implicit
- implementation placement is mechanical rather than interpretive
- the first upstream slice and first downstream slice can be implemented
  without inventing
  ids, claim bundles, values, or reader cutovers

## Phase 1. Land `EvidenceSet`

Goal:

- make deterministic evidence selection and typed observation capture
  the formal first pipeline product

Deliver:

- capture-scoped `EvidenceSet` emission keyed by `evidence_set_id`
- deterministic selected, superseded, and blocked evidence membership
- typed evidence observations that survive beyond intake heuristics, including
  field tables frozen for the first upstream slice for
  `statement_document` and `statement_balance_row`
- bridge compatibility view for `translation_input_plan.json`

Exit criteria:

- the runtime can explain why every selected evidence member won and why every
  superseded or blocked member did not
- evidence selection becomes authoritative through `EvidenceSet` for the
  in-scope slice

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
- shared gap, review, and readiness records and sidecars attached to claim
  scopes where needed
- declared compatibility views for `EconomicActivityDraft` and
  `SourceTranslationBatch`, with legacy hint fields kept outside `ClaimSet`
  kernels

Exit criteria:

- ambiguous source meaning can remain explicit without being forced into final
  economic meaning
- claim-bundle decisions remain claim-owned and do not carry economic
  truth

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

- `ContinuitySegmentRecord`, `EventLinkRecord`, `BalanceTargetRecord`, and
  `CheckpointProposalRecord`
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

## Phase 6. Land `Journal`

Goal:

- make journal expansion and entry checks a first-class downstream stage

Deliver:

- `JournalEntryRecord`, `PostingRecord`, and `EntryCheckRecord`
- journal-owned blockers and entry-check rules
- rendering orchestration over accepted upstream products

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
- filing-critical policy outputs derived from accepted upstream products rather than
  CoinTracking tax reports

Exit criteria:

- `2023` to `2025` outputs can be produced from reconciled economics and
  accepted checkpoint truth without treating CoinTracking tax reports as the
  ledger

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
