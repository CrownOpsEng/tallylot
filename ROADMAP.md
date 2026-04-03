# Roadmap

This file is the forward implementation anchor for future agents and engineers.
It tracks deferred work, explicit non-goals for the current phase, and design
decisions that should not be rediscovered from scratch.

## Current Phase

- Single-package Python architecture under `src/tallylot/`
- External workspace model only
- CLI and library runtime only
- Filesystem-backed operational storage
- One concrete CoinTracking CSV output adapter is implemented today
- Real source adapters are implemented for Coinbase, Wealthsimple, Binance,
  Crypto.com, Shakepay, Ledger Live, Near, Ronin, GTrade, EVM explorer, EVM
  wallet-state, and the generic structured CSV surface
- Normalization writes `facts.csv`, `fact_annotations.json`, `balances.csv`,
  `balance_evidence.csv`, `exceptions.csv`, and
  `normalization_reviews.csv` as active runtime artifacts
- `facts.csv` now requires `schema_version`, persists signed leg quantities plus
  `instrument_id`, and treats regeneration from raw evidence as the recovery
  path after schema breaks
- `balances.csv` and `balance_evidence.csv` now persist `instrument_id` plus
  `as_of_at` and `as_of_precision`
- Dev-only oracle workflows run through `uv run python -m tools.oracles.cli`
  and stay outside the production package and production CLI surface
- Archive-aware source scanning and intake plan/apply workflows
- Provider-agnostic AI interfaces with stub implementations
- MIT-licensed package with CI-verified wheel and source distribution builds

## Locked Design Decisions For The Next Major Phase

- Complete fact-path alignment before expanding reconciliation, accounting, or
  tax behavior. The branch-level alignment work may break the current fact
  artifact schema directly rather than preserving a compatibility lane.
- Build deterministic reconciliation and source-backed checkpoints before tax
  computation. Run minimal accounting projection work in parallel once the
  canonical fact path stabilizes. Reconciliation remains the trust gate before
  tax; accounting remains the journal coverage and balance gate.
- Treat CoinTracking as one ordinary output adapter plus one dev-only oracle
  family, not as the central business model or implemented center.
- Keep CoinTracking rendering isolated to output-adapter packages and keep
  oracle comparison code outside `src/tallylot/`.
- Keep repo-owned workspace control files generic and operator-facing.
  CoinTracking-specific workflow naming belongs only in concrete edge adapter,
  oracle, or historical baseline references.
- Build shared adapter-layer support for stable translation chores such as file
  traversal, file-family dispatch, row-context handling, draft compilation, and
  wallet evidence construction so provider adapters stay thin.
- Build shared adapter-layer support for source-contract numeric validation
  such as decimal precision expectations so adapters can validate displayed
  raw-text fractional digits and require exact or minimum scale without
  duplicating field-scale logic.
- Keep source adapters translation-only:
  - provider-local parsing
  - provider-local translation rules
  - optional provider-local wallet evidence rules
- Keep shared adapter support adapter-agnostic. It may operate on manifests,
  capabilities, translation contracts, and projection contracts resolved
  through registries, but it must not hard-code knowledge of concrete adapter
  ids or provider families.
- Keep adapter glue out of provider modules. The core and shared adapter
  support layers should own repetitive compilation, projection, and
  balance-derivation behavior.
- Keep the core runtime platform-agnostic: normal reconstruction, checkpoint,
  accounting, and tax workflows must run from source evidence and intentional
  checkpoints without requiring CoinTracking tax or accounting outputs.
- Keep the internal engine asset-class-agnostic. Crypto may remain the first
  implemented policy surface, but new core abstractions should be chosen so FX,
  securities, and similar tracking or tax workflows can fit through adapters
  and policy seams without another domain-center rewrite.
- Introduce a provider-neutral transaction fact model as the new system of
  record. Replace the current normalized transaction shape directly instead of
  carrying forward compatibility wrappers or parallel legacy names.
- Keep canonical identity instrument-based:
  - facts, evidence, and downstream projections use `InstrumentId`
  - symbols, venue identifiers, and chain contracts are identifier inputs, not
    canonical identity
  - unresolved or ambiguous identifier resolution must emit review output and
    block fact emission for the affected activity
- Keep canonical leg math sign-based:
  - facts and downstream services use signed `quantity`
  - positive quantity increases the balance of the leg location; negative
    quantity decreases it
  - output adapters may impose narrower native render policies and must fail
    explicitly on unsupported shapes
- Keep canonical fact timing explicit:
  - facts include `effective_at` plus `effective_precision`
  - adapters must preserve the difference between a date-only effective value
    and an exact timestamp, including exact midnight timestamps
  - execution timestamps and effective-time values are not interchangeable
  - any repo field that may be either date-only or exact-time uses the same
    `*_at` plus `*_precision` convention
- Keep canonical on-chain location identity identifier-rooted and network- or
  chain-scoped:
  - EVM-family locations use `evm:<network>:<address>`
  - chain-specific non-EVM locations use their chain namespace such as
    `near:<account>`, `bitcoin:<address>`, `tron:<address>`, or
    `solana:<address>`
  - derived on-chain sublocations append a stable suffix such as
    `near:<account>:staking`
  - friendly source labels, wallet names, and output labels must not become
    canonical runtime location ids
- Keep file-family routing content-first:
  - source adapters classify recognized export families from schema or content
    signatures before filename hints
  - filename or path hints may break ties only when content does not establish
    ownership
  - translation support should consume adapter-declared family ids instead of
    rediscovering provider filenames in each workflow
- Hard-block mixed raw captures that combine incompatible adapter families in
  one source directory. Profiles with blocking scan issues must not proceed to
  normalization.
- Treat display-rounded numeric exports as non-authoritative when the adapter
  contract requires more source precision. Adapters may omit affected legs and
  emit explicit reviews rather than silently booking rounded values.
- Treat wallet-state evidence as ownership evidence only when the export proves
  chain-scoped or chain-specific account identity. UI identity maps and
  friendly labels are labels only, not canonical ownership records.
- Keep the production layer roots explicit:
  - `domain/`
  - `application/`
  - `ports/`
  - `adapters/sources/`
  - `adapters/outputs/`
  - `infrastructure/`
  - `interfaces/`
- Keep `application/` capability-first rather than bucketed by generic role
  names such as `services` or `models`.
- Keep classification layered:
  - provider-neutral economic kind
  - output projection type
  - journal intent
  - tax treatment code
- Keep journaling replaceable behind a renderer port. Ledger CLI is the first
  validation target, but the domain must not depend on one concrete ledger
  implementation.
- Keep tax policy replaceable behind a policy port. Canadian capital-account
  treatment is the only required implementation for the next phase, but the
  core model must stay jurisdiction-neutral.
- Expand `pydantic` at boundaries only:
  - config
  - external artifact parsing
  - report row validation
  - CLI or API request validation
  - discovery-time manifest validation
- Keep the domain centered on frozen dataclasses, enums, and value objects so
  business invariants remain explicit and independent of framework behavior.
- Keep internal projection metadata neutral. Renderer-specific labels such as
  CoinTracking row types belong in output adapters rather than in domain enum
  values, source adapters, or stored fact artifacts.
- Support the required CoinTracking output taxonomy inside output adapters and
  shared projection contracts without requiring provider-local mapping helpers.
- Keep CoinTracking tax reports, roll-forward outputs, average purchase price,
  and double-entry reports in the oracle lane only. They may support
  comparison, regression, and one-time review, but they must not become normal
  runtime inputs or hidden dependencies.
- Preserve deterministic correction support as a first-class capability.
  Redistribution, supersession, and de-duplication fixes must be modeled in
  data and rules, not as ad hoc operator memory.

## Deferred Work

### HTTP, API, And Agent Runtime

- Add a thin HTTP layer only over the existing application capabilities and
  typed use-case contracts.
- Do not let HTTP handlers own business rules, serialization policy, or adapter
  orchestration.
- Keep CLI, API, and agent requests on the same service contracts.
- Move application-facing request and response DTOs toward resource-oriented
  contracts so interfaces stop exposing raw filesystem `Path` assumptions as
  the long-term boundary shape.
- Prefer job handles plus artifact references for long-running workflows rather
  than interface-owned temporary paths or ad hoc shell coupling.
- Keep agent-facing mutation paths explicit, typed, and auditable; AI/model
  providers remain read-only with respect to ledger mutation.

### Database Adoption

- Replace filesystem-backed fact and evidence storage with a real SQLite-backed
  implementation behind typed repository ports.
- Keep raw evidence as files even after database adoption.
- Add migrations only when the SQLite implementation becomes active.

### Self-Contained AI Runtime

- Add provider-backed `ModelGateway` implementations for OpenAI and OAuth-based
  providers.
- Keep model providers read-only with respect to ledger mutation.
- Persist prompts, review findings, and evidence references in a structured
  audit trail.

### Source Adapter Expansion

- Add real blockchain adapters under `adapters/sources/explorers/` when they
  normalize exported blockchain evidence, or under `adapters/sources/stubs/`
  only while the entry point remains reserved.
- Add real platform API adapters under `adapters/sources/platforms/` when they
  become productized, or under `adapters/sources/stubs/` while they remain
  reserved.
- Keep adapters self-contained with tests and metadata colocated.
- Preserve auto-discovery and fail fast on malformed adapter metadata.

## Rules For Future Work

- Do not reintroduce repo-local live workspace assumptions.
- Keep docs-to-runtime capability parity as an explicit invariant. If a command,
  artifact, or agent entrypoint is documented as active, it must exist and be
  tested.
- Keep `main` squash-merged through PRs only. PR titles must use the
  Conventional Commit subject format, and PR bodies must include `Why:`,
  `What:`, `Checks:`, and chronological `Included checkpoints:` sections
  because that metadata becomes the mainline commit record.
- Keep the retired legacy workspace roots out of git:
  `00_docs/`, `01_raw_exports/`, `02_working/`, `03_analysis/`,
  `04_import_ready/`, and `05_outputs/`.
- Keep repo-owned runbooks and agent-facing guides under `docs/`, and keep
  repo-owned workspace subtree guidance and templates under `docs/workspace/`.
- Treat workspace docs under the external root as live working copies or
  operator artifacts, not as the version-controlled source of truth.
- If workspace docs are ever refreshed or seeded beyond the minimal README,
  derive them from the repo-owned docs instead of maintaining a second manual
  documentation branch.
- Do not add compatibility wrappers for removed legacy scripts.
- Do not let adapters reach across layers into CLI or config code.
- Keep the agent guidance router-first: `AGENTS.md` should stay short and direct
  agents to narrow task-specific docs rather than front-loading broad repo
  context.
- Treat `docs/architecture/engineering-standards.md` as the code placement, typing,
  modularization, and naming contract.
- Treat `docs/architecture/commit-standards.md` as the commit message and stable-checkpoint
  contract. Use Conventional Commits and prefer small cohesive checkpoint
  commits without forcing micro-commit overhead.
- Keep application services on port contracts for adapter resolution and artifact
  persistence; do not import infrastructure modules from `application/`.
- Keep pure workflow helper logic in the owning application capability package
  instead of importing infrastructure convenience modules just to share code.
- Keep filesystem scans deterministic. Services that enumerate trees must use a
  stable scan contract with explicit output exclusions rather than ad hoc
  `rglob()` behavior.
- Keep archive inspection centralized. ZIP handling, archive safety limits, and
  archive-member issue reporting belong in the shared scan layer rather than in
  source-specific adapters or CLI commands.
- Keep raw-evidence protections strict. Profiling and normalization outputs must
  not be written inside raw evidence trees.
- Keep packaging release-safe: wheels should ship only the
  `src/tallylot/` package, source distributions must remain
  buildable from a clean checkout, and CI should continue verifying the build
  plus an installable CLI entry point.
- Do not bypass `Decimal` with float-based financial calculations.
- Keep transaction facts structurally strict: every fact must retain at least
  one non-zero economic leg and canonical leg quantities must be signed
  `Decimal` values.
- Keep one canonical `legs` tuple only. Do not reintroduce `fee_legs`,
  `is_fee`, or any other fee-only storage lane in facts, drafts, or
  persistence.
- Keep leg semantics explicit per leg. Every leg carries canonical `LegKind`
  plus optional adapter detail `subtype`; fact classification remains a
  separate fact-level concern.
- Keep fact shape policy explicit and adapter-declared. `FactLegPolicy` uses
  per-kind `LegShapeLimit` entries with explicit minimum and maximum counts,
  unspecified kinds are disallowed, zero-`primary` shapes are opt-in, and
  adapters must declare policy intentionally on emitted drafts rather than
  relying on hidden defaults in the core.
- Keep non-primary attribution metadata narrow. `attributed_to_leg_id` is
  optional metadata on non-`primary` legs only, and it is valid only when it
  references one concrete leg in the same fact. Leg order is not a stable
  identity contract.
- Do not reintroduce convenience selectors such as `asset_in`, `amount_out`,
  or `fee_amount`. Engine code must consume canonical `legs` directly.
- Keep CoinTracking strict at the edge. Its render policy supports one inbound
  `primary`, one outbound `primary`, and one `charge` leg with at least one
  `primary` required; unsupported shapes must fail explicitly rather than
  truncate.
- Keep draft-only provenance references and review markers in
  `fact_annotations.json` keyed by `fact_id` rather than dropping them during
  draft-to-fact compilation or embedding them as CoinTracking-specific
  metadata.
- Keep `BalanceEvidence` owned by `domain/reconciliation`; checkpoint state is
  downstream of reconciliation rather than a second owner of the same model.
- Do not reintroduce a legacy fact `category` bridge. Layered classification
  fields are the stable center; compatibility labels belong only at adapter
  edges.
- Normalize raw sign conventions inside adapters into signed canonical
  quantities. If the provider direction signal is ambiguous or conflicts with
  other fields, surface an issue instead of guessing. When adapters do apply an
  interpretive normalization or fallback default, emit normalization review
  records so users can validate the behavior explicitly.
- When a source export field is only a display-rounded value, adapters must not
  silently book it as authoritative economic data. Require the published
  precision contract when one exists, otherwise emit an issue or review. Ronin
  explorer `TxnFee(RON)` is a current example: non-zero values with fewer than
  nine fractional digits are treated as rounded and are omitted from fee legs.
- Keep source-derived runtime balances application-owned unless the source
  provides true balance evidence. Adapters should not synthesize balance
  snapshots from translated activity rows.
- Keep normalization review artifacts separate from hard issues: invalid or
  unsupported data stays in exceptions, while assumption-driven transforms and
  defaults go to normalization review reporting with concise grouped summaries.
- Treat the current fact artifact schema as disposable during this branch:
  - readers must fail fast on unknown `schema_version`
  - old fact artifacts are not a read-compatibility contract
  - rebuilding normalization and checkpoint artifacts from raw evidence is the
    recovery path after the schema break
- Keep normalization windows explicit and internally consistent. Window
  `facts.csv`, `fact_annotations.json`, `balances.csv`, `exceptions.csv`, and
  `normalization_reviews.csv`; do not window `balance_evidence.csv` or
  `wallet_inventory.csv`. Review records must carry `context_timestamp`, and
  normalization summaries must report
  `reviews_outside_normalization_window`.
- Keep runtime datetimes UTC-aware across drafts, facts, balances, and balance
  evidence. Adapter parsing must normalize to UTC before domain construction,
  while persisted artifact timestamp text remains timezone-less and is
  interpreted as UTC on read.
- Keep temporal precision repo-wide and explicit:
  - exact-time fields use UTC-aware `*_at` values
  - fields that may be date-only or exact-time use `*_at` plus
    `*_precision`
  - `*_precision` uses one shared enum with at least `timestamp` and `date`
  - date-only values are not interchangeable with exact midnight timestamps
  - infer precision from the source contract and parsed field shape, not from a
    normalized `00:00:00` value
- Reserve reconciliation naming for fact, checkpoint, and oracle-comparison
  workflows. Candidate-versus-reference CSV comparison stays under `source
  diff` until fact-based reconciliation exists.
- Complete these precursor refactors before broader reconciliation and
  accounting expansion:
  - instrument registry and identifier mapping seam
  - blocking identifier-resolution path with explicit review output
  - signed-leg rewrite
  - attribution rewrite
  - effective-time and precision model
  - schema-version fail-fast guard on fact artifacts
  - storage, balance derivation, and output projection updates
- Do not allow AI providers to mutate ledger records directly.
- Keep normalized evidence references portable by storing source-relative paths
  instead of machine-local absolute paths.
- Fail fast on ambiguous adapter matches and malformed adapter discovery
  contracts instead of silently picking a candidate.
- Keep repo-local agent entrypoints real. If `.claude/commands/` is referenced
  in the docs, those files must exist and describe the current typed workflow.
- Keep adapter discovery narrow: discover only source-category namespaces and
  adapter package entry points so adapter-local tests and helpers can live
  beside the adapter without affecting runtime registration.
- Escalate flat capability clusters into packages once a third related module
  would otherwise be added. Keep at most two tightly related flat siblings for
  one capability before regrouping.
- Keep the shared-surface package seams intact now that they have been split:
  `domain/transactions/`, `interfaces/cli/`, and
  `infrastructure/discovery/adapters/` should keep bounded submodules instead
  of growing back into single-file hubs.
- Preserve the newer workflow seams as packages as they grow:
  `application/profiling/` and `application/intake/plan/` should absorb future
  helpers instead of
  pushing flat `profile_*` or `plan_*` modules back into sibling directories.
- The repo-local operational dataset was migrated to the external workspace on
  2026-03-26. Use this mapping for any future manual recovery or audit work:
  `00_docs -> docs`, `01_raw_exports/source -> evidence/raw/source`,
  `01_raw_exports/portfolio -> evidence/raw/portfolio`,
  `01_raw_exports/incoming -> evidence/raw/incoming`, `02_working -> working`,
  `03_analysis -> analysis`, `05_outputs -> outputs`.
- Treat `evidence/raw/incoming/` as a historical quarantine area for migrated
  catch-all evidence only. New intake should go directly to standard capture
  paths under `evidence/raw/source/` or `evidence/raw/portfolio/`.
- The separate `04_import_ready/` root is retired in the current architecture.
  Keep approved import candidates under `working/import_batches/`.

## Near-Term Enhancements

- Add dedicated CoinTracking oracle readers for `Trade Table`, `Trade List`,
  `Double-entry`, `Roll Forward in CAD`, `Realized Gain or Loss in CAD`, and
  `Average Purchase Price`.
- Add explicit runtime-boundary, classification-matrix, and migration-sequence
  docs so future work does not drift back into CoinTracking-centric design.
- Add deterministic checkpoint assembly and continuity validation centered on
  the best-evidenced balance date around `2026-03-23`.
- Add a journal renderer port and Ledger CLI implementation for hard-gate
  balance validation on supported activity.
- Add a Canadian capital-account tax policy implementation over reconciled
  facts, with explicit unsupported-item reporting and roadmap capture for
  unimplemented cases.
- Add more conservative overlap heuristics and duplicate signatures.
- Evolve the current stable string file-family ids toward stronger schema
  signatures where needed, while keeping translation and profiling centered on
  adapter-declared family contracts rather than filename tables.
- Continue splitting hotspot use-case modules and DTO hubs into bounded
  feature modules before facts, checkpoints, and tax policy add more
  responsibilities.
