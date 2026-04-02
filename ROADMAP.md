# Roadmap

This file is the forward implementation anchor for future agents and engineers.
It tracks deferred work, explicit non-goals for the current phase, and design
decisions that should not be rediscovered from scratch.

## Current Phase

- Single-package Python architecture under `src/tallylot/`
- External workspace model only
- CLI and library runtime only
- Filesystem-backed operational storage
- One concrete CoinTracking CSV edge adapter is implemented today
- Normalization writes `facts.csv`, `balances.csv`, and
  `balance_evidence.csv` as active runtime artifacts
- Dev-only oracle workflows run through `uv run python -m tools.oracles.cli`
  and stay outside the production package and production CLI surface
- Archive-aware source scanning and intake plan/apply workflows
- Provider-agnostic AI interfaces with stub implementations
- MIT-licensed package with CI-verified wheel and source distribution builds

## Locked Design Decisions For The Next Major Phase

- Build deterministic reconciliation and source-backed checkpoints before tax
  computation. The `2023-08-05` CoinTracking export remains a historical oracle
  boundary, not a hard checkpoint.
- Treat CoinTracking as one ordinary output adapter plus one dev-only oracle
  family, not as the central business model.
- Keep CoinTracking rendering isolated to output-adapter packages and keep
  oracle comparison code outside `src/tallylot/`.
- Keep repo-owned workspace control files generic and operator-facing.
  CoinTracking-specific workflow naming belongs only in concrete edge adapter,
  oracle, or historical baseline references.
- Build shared adapter-layer support for stable translation chores such as file
  traversal, file-family dispatch, row-context handling, draft compilation, and
  wallet evidence construction so provider adapters stay thin.
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

### HTTP And API Runtime

- Add a thin HTTP layer only over the existing application capabilities and
  typed use-case contracts.
- Do not let HTTP handlers own business rules, serialization policy, or adapter
  orchestration.
- Keep CLI and API requests on the same service contracts.

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
  one positive-value economic leg, and leg direction must be modeled
  explicitly rather than by signed magnitudes.
- Do not reintroduce a legacy fact `category` bridge. Layered classification
  fields are the stable center; compatibility labels belong only at adapter
  edges.
- Normalize raw sign conventions inside adapters when direction is otherwise
  explicit. If the sign is the only direction signal or it conflicts with other
  fields, surface an issue instead of guessing. When adapters do apply an
  interpretive normalization or fallback default, emit normalization review
  records so users can validate the behavior explicitly.
- Keep source-derived runtime balances application-owned unless the source
  provides true balance evidence. Adapters should not synthesize balance
  snapshots from translated activity rows.
- Keep normalization review artifacts separate from hard issues: invalid or
  unsupported data stays in exceptions, while assumption-driven transforms and
  defaults go to normalization review reporting with concise grouped summaries.
- Reserve reconciliation naming for fact, checkpoint, and oracle-comparison
  workflows. Candidate-versus-reference CSV comparison stays under `source
  diff` until fact-based reconciliation exists.
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
- Expand source profiling to include richer file-family inspection.
- Continue splitting hotspot use-case modules and DTO hubs into bounded
  feature modules before facts, checkpoints, and tax policy add more
  responsibilities.
