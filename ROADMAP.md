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

Goal:

- freeze the contract pages that bounded implementation slices need
- remove architecture ambiguity before broad implementation begins

Broad implementation must not begin until the contract pages freeze these
contracts.

Before that gate is satisfied, only contract-lock alignment and bounded prep
work are allowed. Broad implementation across Phases 1 to 5 remains blocked.

Must freeze:

- `EvidenceSet` record families, ids, cardinality, and intentional
  `selection_fingerprint` identity churn
- critical-path `EvidenceObservationRecord` field tables for
  `statement_document` and `statement_balance_row`
- `ClaimSet` claim-scope, claim-bundle, and claim-bundle-decision model
- critical-path `ClaimRecord` field tables, `observation_refs`, and
  the compatibility sidecar boundary for retained legacy hint fields
- `AssertionValue`, `PositionRef`, and `ContractRef`
- shared gap and review records and sidecars:
  `GapRecord`, `GapExplanation`, `ReviewRecord`,
  `ReviewExplanation`, capability-owned readiness-view locality rules,
  `SubjectRef = [subject_kind, subject_key]`, truthful `claim_scope_id` and
  `balance_target_id` attachments, and the downstream shared-subject seams
  needed for journal and tax records
- product ids, upstream product-ref multiplicity, and the rule that product
  refs use product ids rather than `kernel_scope_id`
- short-first canonical stable ids, catalog-declared owner-local short slots,
  and deterministic boundary checks that require local slots only on declared
  owner-local surfaces and canonical ids everywhere else
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
  families are already known, keeps gap/review roots explicit when the docs
  mean those shared families directly, and keeps the shared `assessment/` root
  split into concrete nested families such as `gap/` and `review/` while
  keeping readiness views and other assessment behavior in the owning
  application slice
- authoritative persistence model, product-owned directory stems, partition
  scopes, sidecar rules, and default filesystem placement
- migration authority rules, compatibility views, reader cutovers, and
  retirement gates
- package ownership and layer placement that keep shared assessment contracts in
  `domain/assessment/`, keep the persisted `assessment/gap/`,
  `assessment/review/` families as storage rules only, and retire shared
  application assessment behavior until a specific capability-owned derived
  read-model package is activated
- defer broader grouped readiness, reporting, portfolio, visualization, and
  investigation architecture until the trigger ladder below fires, allowing
  only filing-critical product-local derived outputs, narrow rendering outputs,
  or migration compatibility views before then
- catalog-first target naming governance with one machine-readable naming
  authority and a blocking `target-naming` check on enforced forward-looking
  docs
- explicit no-invention rules for non-critical observation and claim kinds
- no placeholder valuation-measure field family until a real shared taxonomy
  exists

Deliver:

- aligned contract pages for target products, ontology, gap/review
  records and sidecars, and
  persistence rules
- explicit cutover matrix for bridge-to-target migration
- one first upstream slice and one first downstream slice
- explicit package ownership for `domain/` and `application/`
- explicit defer-until-trigger rules for broader derived read models and
  projections so the tax-first path does not have to invent long-term
  read-model ownership early
- explicit fast-path rule that reducers read kernels, not explanation sidecars
- frozen critical-path field tables and product-id rules that later writing
  work can merge without deciding new structure
- a documented completion gate that names the owner docs and concrete reader
  inventory required before broad implementation begins

### Phase 0 Completion Gate

Treat this checklist as the operational gate for ending Phase 0, not as a
claim that the repo has already satisfied it.

Owner docs that must align before broad implementation begins:

- `ROADMAP.md`
- `docs/status/migration-sequence.md`
- `docs/concepts/bridge-to-target-mapping.md`
- `docs/concepts/pipeline-stage-contracts.md`
- `docs/concepts/domain-ontology.md`
- `docs/concepts/gaps-and-reviews.md`
- `docs/concepts/reconciliation-tax-architecture.md`
- `docs/reference/first-upstream-slice-contract.md`
- `docs/reference/first-downstream-slice-contract.md`

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
- `TaxOutputs` can land without requiring a separate read-side architecture
  first
- no shared application assessment center or shared grouped-readiness family is
  left as the default home for later grouped consumers
- the first upstream slice and first downstream slice can be implemented
  without inventing
  ids, claim bundles, values, or reader cutovers
- every active bridge surface has one authoritative target owner
- every active bridge surface has one derived compatibility rule
- every active bridge surface names concrete current readers and concrete
  target readers
- no Phase 1 or Phase 2 doc claims authority over `TransactionFact`,
  `facts.csv`, `balance_snapshots.csv`, `balance_references.csv`, or
  `cointracking_csv`
- `EventLinkRecord` status is aligned between this roadmap and the first
  downstream slice contract
- the intentional looseness of Phases 6 and later is explicit and is
  non-blocking for Phase 0 to Phase 5 implementation

| Exit criterion | Authoritative doc section(s) | Automated proof |
| --- | --- | --- |
| no owner concept is defined in two competing places | `docs/status/migration-sequence.md` `## Roadmap Ownership`; `docs/concepts/bridge-to-target-mapping.md` `## Scope And Related Contract Pages`; `docs/concepts/reconciliation-tax-architecture.md` `## Related Contract Pages` | `test_owner_contract_pages_do_not_compete_for_the_same_authority` |
| no target product references an undefined record family or ref type | `docs/concepts/pipeline-stage-contracts.md` `## Shared Contract References`; `docs/concepts/domain-ontology.md` `## Identity And Ref Seams`; `docs/concepts/gaps-and-reviews.md` `## SubjectRef` | `test_forward_contracts_do_not_reference_undefined_record_families_or_refs` |
| no cross-stage support record or sidecar masquerades as a claim kind | `docs/concepts/pipeline-stage-contracts.md` `### Derived Compatibility Sidecars`; `docs/reference/first-upstream-slice-contract.md` `## ClaimSet Coverage` | `test_critical_path_claim_field_tables_are_unique_and_complete` |
| claim-stage blockers can attach to `claim_scope_id` before subject identity resolves, and later-stage blockers can attach to truthful journal or tax subjects without collapsing to kernel-scope attachment only | `docs/concepts/gaps-and-reviews.md` `## Non-Subject Scope Ids`; `docs/concepts/pipeline-stage-contracts.md` `## ClaimSet`; `docs/concepts/pipeline-stage-contracts.md` `## ReconciliationState` | `test_gap_and_review_attachment_rules_use_truthful_scopes` |
| no target id or helper id bakes bridge-era naming into target identity | `docs/concepts/pipeline-stage-contracts.md` `## EvidenceSet` stable ids; `docs/concepts/pipeline-stage-contracts.md` `## ClaimSet` stable ids; `docs/reference/first-upstream-slice-contract.md` `## Id And Fingerprint Rules` | `test_downstream_identity_recipes_do_not_embed_bridge_nouns` |
| no canonical target contract keeps source-specific crypto nouns such as `wallet` when a repo-owned domain noun already owns that seam | `docs/concepts/domain-ontology.md` `## Generic Model Requirements`; `docs/reference/first-upstream-slice-contract.md` observation and claim tables | `test_forward_target_contracts_keep_source_specific_crypto_nouns_out_of_canonical_fields` |
| no bridge surface is left without an authority and retirement rule | `docs/concepts/bridge-to-target-mapping.md` `## Cutover Matrix`; `docs/status/migration-sequence.md` `## Bridge Retirement Rules` | `test_bridge_cutover_matrix_rows_are_complete` |
| no hot-path field points to an undefined value ref or sidecar | `docs/concepts/pipeline-stage-contracts.md` `## ReconciliationState`; `docs/concepts/pipeline-stage-contracts.md` `## Checkpoint`; `docs/reference/first-downstream-slice-contract.md` `## In-Scope Record Families` | `test_reconciliation_and_checkpoint_hot_path_fields_use_direct_values` |
| every critical-path observation and claim kind has one authoritative kernel field table | `docs/concepts/pipeline-stage-contracts.md` `### First-Slice Critical-Path Observation Kinds`; `docs/concepts/pipeline-stage-contracts.md` `### First-Slice Critical-Path Claim Kinds`; `docs/reference/first-upstream-slice-contract.md` matching field-table sections | `test_critical_path_observation_field_tables_are_unique_and_complete`; `test_critical_path_claim_field_tables_are_unique_and_complete` |
| no target product ref in a product header uses `kernel_scope_id` where a product id exists | `docs/concepts/pipeline-stage-contracts.md` `### Product Id And Upstream Ref Rules`; `docs/reference/first-downstream-slice-contract.md` `## Product Header And Downstream Inputs`; `docs/concepts/reconciliation-tax-architecture.md` `## Authoritative Persistence Model` | `test_product_headers_use_product_ids_not_kernel_scope_id` |
| non-critical observation and claim kinds are explicitly deferred rather than left implicit | `docs/concepts/pipeline-stage-contracts.md` critical-path sections; `docs/reference/first-upstream-slice-contract.md` out-of-scope and valuation-measure rules | `test_noncritical_observation_and_claim_work_is_explicitly_deferred` |
| implementation placement is mechanical rather than interpretive | `docs/concepts/domain-ontology.md` `## Required Package Ownership`; `docs/concepts/gaps-and-reviews.md` `## Readiness Locality` | `test_forward_contracts_keep_placement_mechanical` |
| `TaxOutputs` can land without requiring a separate read-side architecture first | `ROADMAP.md` `## Deferred Read-Model Activation Triggers`; `docs/concepts/architecture-overview.md` `## Runtime Posture`; `docs/concepts/reconciliation-tax-architecture.md` `## Authoritative Persistence Model`; `docs/concepts/gaps-and-reviews.md` `## Readiness Locality` | `test_tax_outputs_contract_does_not_require_general_read_side_activation` |
| no shared application assessment center or shared grouped-readiness family is left as the default home for later grouped consumers | `docs/concepts/domain-ontology.md` `## Required Package Ownership`; `docs/concepts/gaps-and-reviews.md` `## Readiness Locality`; `docs/concepts/reconciliation-tax-architecture.md` `### Assessment, Product-Local Detail, Compatibility, And Derived Outputs` | `test_forward_contracts_keep_placement_mechanical` |
| the first upstream slice and first downstream slice can be implemented without inventing ids, claim bundles, values, or reader cutovers | `docs/reference/first-upstream-slice-contract.md` `## Id And Fingerprint Rules` and `## Bridge Compatibility Views`; `docs/reference/first-downstream-slice-contract.md` `## Id And Fingerprint Rules` and `## Bridge Compatibility Views` | `test_slice_contracts_freeze_ids_values_and_reader_cutovers` |
| every active bridge surface has one authoritative target owner | `docs/concepts/bridge-to-target-mapping.md` `## Cutover Matrix` | `test_bridge_cutover_matrix_rows_are_complete` |
| every active bridge surface has one derived compatibility rule | `docs/concepts/bridge-to-target-mapping.md` `## Cutover Matrix` | `test_bridge_cutover_matrix_rows_are_complete` |
| every active bridge surface names concrete current readers and concrete target readers | `docs/status/migration-sequence.md` `## Canonical Current-Reader Inventory`; `docs/concepts/bridge-to-target-mapping.md` `## Cutover Matrix` | `test_bridge_cutover_matrix_matches_declared_reader_inventory`; `test_bridge_cutover_matrix_rows_are_complete` |
| no Phase 1 or Phase 2 doc claims authority over `TransactionFact`, `facts.csv`, `balance_snapshots.csv`, `balance_references.csv`, or `cointracking_csv` | `ROADMAP.md` Phase 1. Land EvidenceSet; `ROADMAP.md` Phase 2. Land ClaimSet; `docs/status/migration-sequence.md` `### 3. First Downstream Slice` | `test_early_stage_docs_do_not_claim_authority_over_later_bridge_outputs` |
| `EventLinkRecord` status is aligned between this roadmap and the first downstream slice contract | `ROADMAP.md` Phase 4. Land ReconciliationState; `docs/concepts/pipeline-stage-contracts.md` `## ReconciliationState`; `docs/reference/first-downstream-slice-contract.md` `## In-Scope Record Families` | `test_event_link_scope_is_consistent_across_forward_contracts` |
| the intentional looseness of later phases is explicit and remains non-blocking for the near-term implementation sequence | `ROADMAP.md` post-Phase 5 transition note; `docs/status/migration-sequence.md` `### 5. Later Downstream Products` | `test_later_phase_docs_remain_explicitly_high_level`; `test_completion_gate_maps_exit_criteria_to_authoritative_docs_and_automated_proof` |

## Deferred Read-Model Activation Triggers

The tax-first window keeps the staged pipeline authoritative and defers
capability-owned derived read models and projections until one of the triggers
below fires.

### Trigger A. Second Grouped Non-Compatibility Consumer

Fire before implementation if the repo is about to add any grouped consumer
beyond filing-critical `TaxOutputs`, existing narrow rendering behavior, or
migration compatibility views.

Examples:

- operator-facing grouped readiness summary
- non-tax grouped report
- grouped dashboard dataset
- holdings or portfolio summary

Response:

- introduce `docs/concepts/query-projection-architecture.md`
- make the triggered slice first-class in architecture overview, ontology,
  standards, and naming governance
- do not ship the new grouped consumer inside a stage package first

### Trigger B. First Persisted Derived Grouped Surface Outside Tax Outputs Or Compatibility

Fire before implementation if a grouped non-authoritative surface needs durable
persistence and is not a compatibility view or a product-local tax-output
surface.

Response:

- introduce a non-authoritative projection root under
  `working/projections/<slice>/<projection_family>/...`
- define projection identity as slice-local and derived from authoritative refs
  plus slice parameters
- keep projections explicitly non-canonical and regenerable

### Trigger C. First Feature That Clearly Belongs To A Reserved Family

Fire before implementation when one of these appears:

- cross-stage or cross-product reporting
- portfolio tracking or holdings views
- charts, dashboards, or visualization datasets
- investigation or drill-down workflows that are not compatibility-only

Response:

- create only the specific needed package:
  application/reporting/, application/portfolio/,
  application/visualization/, or application/investigation/
- do not pre-create all reserved families

### Trigger D. Copy Pressure Across Stage Packages

Fire before implementation if grouped output logic would otherwise be copied
into a second stage package or second consumer.

Response:

- extract to the correct capability-owned derived read-model package in the
  same slice as the new feature
- do not ship the duplicate first and clean it up later

### Trigger E. Automatic Activation At Post-Filing Expansion

If none of the earlier triggers fire first, activate the broader derived
read-model and projection architecture at the start of `Phase 10`.

Response:

- add `docs/concepts/query-projection-architecture.md`
- add the needed package families to naming governance
- add projection persistence rules
- update architecture overview and standards to make the capability-owned
  derived read side explicit

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
