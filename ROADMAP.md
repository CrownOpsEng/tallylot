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

The current runtime now uses one shared balance capability across
normalization, reconciliation, and checkpoint submission. Balance state is
expressed as derived `balance_snapshots.csv` plus unified
`balance_references.csv`, where each reference row declares its
`reference_kind`.

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
- center intake on explicit capture identity, capture registries, and
  raw-evidence preservation instead of inferred capture buckets
- keep inferred period and capture heuristics as report metadata only; they do
  not control runtime identity, routing, or normalization ownership
- finish adapter parity and projection parity coverage on the current fact
  model
- keep review and issue outputs explicit for ambiguous direction, precision, or
  classification decisions
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
- add a repo-native semantic parity validator for unchanged raw inputs

Exit criteria:

- supported adapters emit facts without normalized-transaction-era wrapper
  lanes
- CoinTracking CSV projection remains correct from facts alone
- remaining normalization ambiguity paths emit explicit reviews or blocking
  issues instead of silent coercion
- balance references, issue rows, review rows, and location inventory evidence
  rows share one flattened provenance locator family at artifact boundaries
  while runtime models keep typed provenance
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
- keep target planning, snapshot derivation, reference resolution, hydration,
  and assertion assembly behind the shared balance capability
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

### 4. Checkpoint Packages And Opening State

Formalize typed checkpoint packages as the handoff between reconstruction,
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
- pooled ACB state
- disposition outputs
- income outputs
- unsupported tax item outputs
- carry-forward and year summary outputs for `2023`, `2024`, and `2025`

Exit criteria:

- `2023` to `2025` tax artifacts emit from reconciled facts
- year-end and carry-forward state is reproducible without tracker tax reports
- unresolved unsupported tax items are visible rather than hidden in notes

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
