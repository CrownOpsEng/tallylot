---
title: "Adapter Delivery Plan"
summary: "Filing-first plan for stabilizing current adapters now and deferring the unified adapter contract rewrite until after filing-critical work."
doc_type: status
audience: human
owner: repo
status: active
nav_order: 30
related:
  - ROADMAP.md
  - docs/guides/write-an-adapter.md
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/domain-ontology.md
  - docs/concepts/reconciliation-tax-architecture.md
  - docs/status/current-state.md
---

Use this plan when deciding whether adapter work belongs in the current
filing-critical window or in the later adapter-contract rewrite.

The intent is to keep tax delivery primary. The repo should harden the current
adapter path where it directly improves filing confidence, determinism, and
repeatability, but it should defer the full unified adapter redesign until the
filing path is stable enough to trust.

## Decision

The repo should use a filing-first adapter strategy:

- harden the current adapter layer where it directly reduces filing risk
- avoid a broad source and output adapter contract rewrite before filing
- extract only those shared boundaries that remove current drift on the filing path
- write down the future unified adapter design now, but migrate to it later

This plan treats adapter work as three tracks:

- `now`: filing-critical hardening on the current adapter boundaries
- `prep`: first-principles unified adapter contract and bridge-mapping work
  needed by shared foundations and the first target-stage increment
- `roadmap`: broader family migration into the unified adapter contract once the
  filing path and first increment are stable

Forward-looking adapter work must map into the main runtime pipeline in
`docs/concepts/pipeline-stage-contracts.md` and the trust-gate rules in
`docs/concepts/reconciliation-tax-architecture.md`. Adapter docs do not define
their own competing meaning for `EvidenceSet`, `ClaimSet`, `EconomicFacts`,
`ReconciliationState`, `Checkpoint`, `Journal`, `TaxInputs`, or
`TaxOutputs`.

## Why This Plan Exists

The current adapter layer already carries much more responsibility than a
single translation interface suggests.

Today a source adapter may be responsible for:

- source matching during profile selection
- file-family classification during profile analysis
- intake file matching and route selection
- timezone validation policy
- location inventory extraction
- statement PDF recognition and parsing
- statement instrument claim resolution
- translation input planning in planner-enabled adapters
- translation from raw evidence into shared activity drafts, issues, reviews,
  balance references, and location inventory

Today an output adapter is responsible for:

- declaring supported render policy and fact-shape requirements
- rendering facts into an external artifact

This mismatch matters because the current source contract is effectively a
bundle of unrelated jobs. That makes it easy for behavior drift to accumulate
between adapters and makes every contract cleanup larger than it needs to be.

The repo still needs a broad redesign, but taxes depend on deterministic
current behavior sooner than they depend on a perfect future contract.

## Current Adapter Scope

### Current Source-Side Jobs

| Job | Current boundary | Why it matters |
| --- | --- | --- |
| Source selection | `match(...)` | Chooses the owning adapter for profiling and normalization. |
| File-family recognition | `classify_profile_families(...)` | Drives deterministic family ownership before translation. |
| Intake classification | `match_intake(...)`, `route_intake(...)` | Controls where inbound files land in the workspace. |
| Timezone policy | `validate_profile_timezones(...)` | Prevents silent timestamp drift. |
| Location evidence | `extract_location_inventory(...)` | Supplies owned location identity and evidence. |
| Statement parsing | `match_statement_document(...)`, `parse_statement_document(...)` | Converts statements into quantity-backed balance evidence. |
| Statement identity claims | `resolve_statement_instrument_claims(...)` | Resolves statement rows to shared instrument identities. |
| Translation planning | `describe_translation_inputs(...)`, `translate_selected_inputs(...)` | Prevents adapter-local file winner heuristics. |
| Translation | `translate(...)` | Produces activity drafts and evidence artifacts. |

### Current Output-Side Jobs

| Job | Current boundary | Why it matters |
| --- | --- | --- |
| Output policy declaration | `render_policy` | Rejects facts that the target format cannot represent safely. |
| Rendering | `render(...)` | Produces deterministic external output artifacts. |

### Current Adapters

| Adapter | Kind | Current role | Default filing priority |
| --- | --- | --- | --- |
| `coinbase` | source platform | retail export translation, planner path, statement parsing | Tier A when the filing workspace uses Coinbase |
| `binance` | source platform | multifamily CSV translation, intake routing, statement parsing | Tier A when the filing workspace uses Binance |
| `shakepay` | source platform | translation, statement parsing, statement evidence | Tier A when the filing workspace uses Shakepay |
| `wealthsimple` | source platform | translation, intake routing | Tier A when the filing workspace uses Wealthsimple |
| `ledger_live` | source wallet | grouped-operation translation, wallet inventory | Tier A when the filing workspace uses Ledger Live |
| `evm_explorer` | source explorer | translation, address extraction, portfolio evidence | Tier A only when explorer evidence is needed for filing |
| `near` | source explorer | translation, location inventory | Tier A only when NEAR activity is part of filing |
| `ronin` | source explorer | translation, location inventory | Tier A only when Ronin activity is part of filing |
| `evm_wallet` | source wallet | wallet inventory, transaction translation | Tier A only when wallet-state evidence is needed |
| `crypto_com` | source platform | translation, intake routing | Tier B unless required in the filing workspace |
| `gtrade` | source platform | translation, intake routing, location inventory | Tier B unless required in the filing workspace |
| `structured_csv` | generic source | generic structured import path | Tier B unless the filing workspace depends on it |
| `cointracking_portfolio` | portfolio intake | intake-only routing of portfolio exports | Tier B for intake stability, not for translation |
| `cointracking_csv` | output | filing-oriented CSV projection | Tier A because output determinism directly affects filing |
| `cointracking_api` | output stub | reserved edge adapter | Tier C |
| `generic_http_output` | output stub | reserved edge adapter | Tier C |
| `platform_api_stub` | source stub | reserved non-runtime adapter | Tier C |
| `blockchain_stub` | source stub | reserved non-runtime adapter | Tier C |

### Priority Tiers

| Tier | Meaning | Action in this plan |
| --- | --- | --- |
| Tier A | Required for the current filing workspace or filing output path | Harden now. |
| Tier B | Supported but not required for the current filing window | Only touch if a shared fix naturally improves it at low cost. |
| Tier C | Stubbed, reserved, or clearly non-filing | Do not expand now. Roadmap only. |

The actual Tier A set must be driven by the active filing workspace, not by a
desire for repo-wide completeness.

## Filing-First Principles

- Prefer deterministic current behavior over ambitious interface redesign.
- Prefer shared support extraction over copy-paste repairs when the shared boundary
  is already visible.
- Prefer explicit issues and reviews over adapter-local guesswork.
- Prefer content signatures, coverage metadata, and fingerprints over filename
  or lexical path order.
- Prefer one shared statement extraction path over adapter-local statement
  orchestration.
- Prefer one shared output-policy gate over format-specific silent coercion.
- Do not widen the current source adapter contract during the filing window.
- Do not introduce dual contracts, migration wrappers, or adapter-local
  compatibility shims for the future design.

## Work To Do Now

The `now` track is the work that should land before or during filing as long as
the active filing path benefits directly.

### 1. Lock The Filing-Critical Adapter Set

Before additional adapter work begins, determine which current adapters are
actually in the filing path for the active workspace.

Required actions:

- list every source used by the current filing workspace for `2023` to `2025`
- map each source to one current adapter id
- identify which outputs are filing-critical, beginning with
  `cointracking_csv`
- mark all other adapters as non-blocking for the current filing window

Deliverables:

- one repo-safe filing adapter set recorded in the active delivery notes or
  issue thread
- one explicit decision on whether each non-filing adapter is Tier B or Tier C

Out of scope now:

- broad parity work for adapters not used in the current filing path
- redesigning discovery to support future adapter kinds

Repo-status rule:

- this repo may freeze the default Coinbase-first slice and its contract
  boundaries
- this repo must not pretend it already knows the actual `2023` to `2025`
  filing adapter inventory without an external workspace source list

Exit criteria:

- the team can say exactly which adapters must be stable before filing

### 2. Harden Shared Determinism Surfaces

These shared areas reduce drift across multiple adapters and are worth
changing during the filing window.

| Work item | Why now | Concrete work | Explicitly out of scope | Exit criteria |
| --- | --- | --- | --- | --- |
| Translation input selection | File winner logic is one of the biggest drift sources. | Finish planner migration for filing-critical adapters, remove path-order and filename-order winning logic, keep selected, superseded, and blocked candidates explicit. | A new global adapter DSL. | Unchanged raw inputs pick the same candidates every run and emit the same plan artifacts. |
| Deterministic ordering | Output drift can come from unordered iteration even when facts are correct. | Canonicalize ordering for candidates, selected files, drafts, issues, reviews, balance references, and rendered rows where the target format permits it. | New storage formats. | Repeated normalization and rendering runs are byte-stable or field-stable on unchanged inputs. |
| Shared file-family recognition | Family ownership drift creates downstream translation drift. | Prefer content and schema signatures, publish stable family ids, and keep family claims in profile artifacts authoritative for translation. | Rewriting discovery around the future facet model. | Filing-critical adapters translate only recognized families and report unmatched files explicitly. |
| Timezone handling | Silent timestamp drift directly changes tax outcomes. | Keep timezone policy explicit, centralize common timezone summaries and review patterns, and reject ambiguous timestamp interpretation. | A universal temporal framework rewrite. | Filing-critical adapters no longer silently coerce naive timestamps into facts. |
| Statement extraction | Statement evidence is needed for checkpoint and balance trust. | Keep one shared PDF extraction path, align statement matching and instrument-claim resolution, and fail explicitly on recognized-but-empty parses. | A new statement plugin system. | Statement-backed balance evidence is deterministic across repeated runs. |
| Identity resolution feedback | Instrument ambiguity must block fact creation consistently. | Keep draft compilation as the shared gate, standardize blocking issue and review paths, and remove adapter-local special cases where possible. | New identity domains or taxonomy expansion. | All unresolved identity paths fail the same way across filing-critical adapters. |
| Output projection validation | Filing outputs cannot rely on renderer guesswork. | Strengthen render-policy checks and keep unsupported fact shapes explicit before rendering. | New output-contract architecture. | The renderer rejects unsupported fact shapes before writing the artifact. |

### 3. Finish Planner Migration Only Where It Reduces Filing Risk

Planner migration is worth doing now only when the adapter still performs
winner-selection internally.

Now:

- finish planner migration for every Tier A adapter that still chooses one file
  by filename, path order, or provider-local winner heuristics
- keep plan artifacts mandatory before translation starts
- ensure candidate description, coverage, freshness, selection mode, and
  comparability are explicit
- block ambiguous overlap instead of selecting implicitly

Later:

- generalize planner support into the future unified adapter contract
- add declarative candidate schemas for every adapter kind

Exit criteria:

- every Tier A adapter uses either a safe planner path or an explicitly
  accepted fallback path with no hidden winner logic

### 4. Reduce Adapter-Local Orchestration In Tier A Adapters

Tier A adapters should stay responsible for provider-local semantics only.
They should not own their own mini workflow engines when a shared boundary
already exists.

Allowed extractions now:

- shared file-family dispatch helpers
- shared timezone summary builders
- shared issue and review builders
- shared statement extraction orchestration
- shared draft compilation
- shared location-id and identifier helpers
- shared deterministic ordering helpers

Avoid now:

- creating another broad `helpers.py` or generic adapter utility sink
- extracting abstractions that are only preparing for the future redesign
- moving provider-local economic semantics into generic support too early

Exit criteria:

- the average Tier A adapter entry point becomes thinner without changing the
  external contract

### 5. Add Replay-Grade Verification For Tier A Adapters

The filing path needs deterministic verification more than it needs a new
contract.

Required verification work:

- maintain golden packs for Tier A adapters with meaningful provider cases
- add or refresh expected fact, balance, issue, and review coverage for
  observed row families
- add parity checks for unchanged raw inputs
- verify that repeated runs preserve:
  - file completeness
  - fact counts
  - balance reference counts
  - issue and review behavior unless a documented expected difference applies
- verify that rendered filing outputs are stable on unchanged facts

Recommended verification focus:

- planner artifacts for planner-enabled adapters
- statement-backed evidence for adapters with PDF support
- grouped or multi-leg operations for complex platform and wallet adapters
- explorer and wallet inventory behavior when location identity is filing
  relevant

Out of scope now:

- repo-wide parity goldens for non-filing adapters
- exhaustive perfection for every unsupported provider edge case

Exit criteria:

- unchanged filing inputs can be rerun with confidence that output drift is a
  real signal, not adapter noise

### 6. Tier A Adapter Work Matrix

This matrix defines what should happen now for each likely filing-relevant
adapter.

| Adapter | Do now | Defer |
| --- | --- | --- |
| `coinbase` | Keep planner path authoritative, harden statement PDF extraction, ensure retail export family claims stay stable, refresh deterministic goldens. | Future facet split and declarative manifest redesign. |
| `binance` | Keep multifamily family recognition explicit, remove hidden winner logic, harden timezone review behavior, verify statement evidence, expand row and family coverage only for observed filing inputs. | Broad cleanup for unsupported export families not in the filing workspace. |
| `shakepay` | Keep statement-backed balances deterministic, ensure translation and statement parsers agree on instrument claims, refresh goldens for observed filing rows. | Contract redesign for statement parsing hooks. |
| `wealthsimple` | Verify deterministic translation and intake behavior for actual filing exports, add missing edge coverage only when observed in the workspace. | Broader portfolio-style abstraction work. |
| `ledger_live` | Harden grouped-operation translation and wallet inventory only if the filing workspace depends on it, especially for swaps and grouped operations. | General wallet-adapter redesign. |
| `evm_explorer` | Keep address extraction, transaction translation, and same-source same-chain portfolio evidence explicit if explorer evidence is needed for filing. | General public-ledger adapter unification and provider-hydration integration. |
| `near` | Harden only if the filing workspace includes NEAR activity. | Family-wide explorer contract redesign. |
| `ronin` | Harden only if the filing workspace includes Ronin activity, including known fee-precision review behavior. | Family-wide explorer contract redesign. |
| `evm_wallet` | Harden only if wallet-state or wallet inventory evidence is needed for filing. | Wallet-state contract redesign. |
| `cointracking_csv` | Keep render-policy validation strict, verify deterministic row ordering and projection coverage for filing facts. | New writer contract or multi-target artifact pipeline. |

### 7. Tier B And Tier C Handling During The Filing Window

Tier B and Tier C adapters are not ignored, but they should not drive the
shape of filing-period work.

Tier B rule:

- accept low-cost shared improvements when they naturally benefit Tier B
  adapters
- avoid adapter-specific surgery unless that adapter becomes part of the
  current filing workspace

Tier C rule:

- keep stubs and reserved surfaces minimal
- do not expand stub capabilities during the filing window

### 8. Explicitly Deferred Work

The following work should be roadmapped, not pulled into the filing window:

- replacing the monolithic `SourceAdapter` contract with a new multi-facet
  interface
- unifying input, portfolio, and output adapters under one new runtime
  contract
- redesigning discovery around future adapter kinds
- introducing adapter migration wrappers, compatibility shims, or dual-write
  flows
- creating a fully declarative adapter specification language
- broad parity work for non-filing adapters
- generalized balance-provider integration work beyond filing-critical needs

### 9. Filing-Window Exit Criteria

The `now` track is complete when all of the following are true for the active
filing workspace:

- every filing-critical source is mapped to one supported adapter
- planner-enabled Tier A adapters emit stable planning artifacts before
  translation
- Tier A adapters no longer depend on hidden lexical winner selection
- timestamp interpretation is explicit and stable
- statement-backed balance evidence is deterministic where used
- unchanged raw inputs preserve expected fact and evidence behavior
- `cointracking_csv` rendering is stable and rejects unsupported fact shapes
- remaining unsupported or ambiguous cases surface as explicit issues or
  reviews

The filing window does not require every adapter to be elegant. It requires
the filing path to be trustworthy.

## Work To Advance During Shared Foundations

The `prep` track is allowed before the full adapter migration because Phase 0
cannot safely proceed on stage contracts alone. The repo also needs adapter
product and bridge-mapping rules that let `EvidenceSet` and `ClaimSet` land
without creating a second architecture center or forcing a brutal later
rewrite.

### 1. Freeze Adapter Product Contracts Needed By The First Slice

Write and align the minimum adapter-scoped products needed by shared
foundations and the first vertical slice:

- `EvidenceSet`
- `ClaimSet`
- `SourceTranslationBatch` as the current bridge seam during migration
- any bounded bridge note needed for `ProjectionBundle` or `ArtifactBundle`

Required rules:

- the adapter-scoped products must map explicitly into the core runtime
  pipeline
- the current bridge seam remains honest current-state truth until a bounded
  replacement slice lands
- target-stage product ownership stays in the core architecture docs, not in
  adapter docs

### 2. Freeze Bridge Mapping From Current Boundaries To Proto Target Products

The first target-stage increment must say exactly how current artifacts map into the
new products.

Required bridge notes:

- how planner-owned candidate and selection artifacts become proto-`EvidenceSet`
- how current translation boundaries, draft compilation, and claim-like diagnostics
  become proto-`ClaimSet`
- where the shared compiler owns meaning versus where adapters remain
  provider-local

Rules:

- no dual active runtime centers
- no adapter-local hidden semantics beyond provider-local meaning
- no broad family migration as a hidden prerequisite for the first increment
- [Bridge To Target Mapping](../concepts/bridge-to-target-mapping.md) is the
  single owner for the primary bridge mapping; this page only records the
  adapter-delivery implications

Default bridge mapping for the first increment:

- [Bridge To Target Mapping](../concepts/bridge-to-target-mapping.md) owns the
  exact planner-candidate, planner-plan, statement-evidence, and bridge-only
  landing rules
- [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md) owns the
  shared claim taxonomy plus the deterministic id, ordering, serialization, and
  fingerprint contracts
- [First Slice Contract](../reference/first-slice-contract.md) owns the bounded
  Coinbase-first evidence families, claim families, replay, parity, and
  allowed-drift rules
- `SourceTranslationBatch` remains the honest current runtime boundary while
  the first increment emits bounded proto-products beside it, and the shared
  compiler keeps ownership of current bridge outputs until the downstream
  target-stage replacement lands

### 3. Freeze Adapter Determinism And Compatibility Rules

Shared foundations need adapter determinism to be a written contract, not only
an implementation preference.

Required prep work:

- declared ordering rules for adapter-scoped products
- schema-version and compatibility rules aligned with target product rules
- stable serialization and fingerprint rules
- explicit ownership of manifest fingerprints versus product fingerprints

### 4. Name The First Adapter-Family Vertical Increment

The first unified-adapter-facing increment should be explicit instead of implied.

Required increment definition:

- one adapter family
- the evidence families and claim families in scope
- the bridge outputs or target products it must still interoperate with
- replay and parity gates on unchanged evidence
- unsupported or ambiguous cases that must remain explicit

Default first-increment direction:

- use the planner-enabled `coinbase` retail export family plus statement-backed
  balance observation flow unless the active filing workspace requires another
  Tier A family to land first
- keep `cointracking_csv` projection compatibility in scope for the same increment
  where it protects filing output determinism
- use [First Slice Contract](../reference/first-slice-contract.md) as the
  bounded parity, replay, and allowed-drift contract for that default increment

### 5. Allow Shared Compiler And Verifier Prep

The repo may advance shared compiler and verifier work during prep when that
work reduces drift across the first increment.

Allowed prep work:

- shared claim compilation boundaries
- shared product verifiers
- shared replay and fingerprint checks
- shared bridge-to-target comparison helpers

Not allowed in prep:

- repo-wide family migration
- wrappers that keep old and new contracts alive indefinitely
- broad facet rollout with no bounded consumer

## Work To Roadmap

The `roadmap` track covers broader family migration and contract adoption after
the shared foundations and first increment are stable enough that the filing path
is not depending on unresolved adapter semantics.

### Roadmap Objective

Replace the current bundled source contract and separate output contract with a
smaller, purpose-defined adapter architecture built around evidence, claims,
explicit bridge boundaries during migration, deterministic verification, and
provider-local semantics only.

### Roadmap Principles

- unify around explicit adapter products, not around one giant method interface
- keep manifests declarative and authoritative
- separate hard assertions from soft annotations
- treat provenance as a first-class runtime concept
- require explicit ordering and fingerprints at artifact boundaries
- keep the compiler and verifier shared
- keep provider-local code focused on parsing, semantic mapping, and rendering

### Roadmap Phase R1. Finish Adapter Products Beyond The First Increment

Complete and extend the future adapter-scoped products beyond the bounded
contracts already needed for the first increment:

- `EvidenceSet`
- `ClaimSet`
- `SourceTranslationBatch` as the current bridge boundary, with a target-direction
  move toward `TranslationResult` only when code changes land
- `ProjectionBundle`
- `ArtifactBundle`

Boundary rule:

- these adapter-scoped products must map explicitly into the core runtime
  pipeline in `docs/concepts/reconciliation-tax-architecture.md`
- adapter planning must not become a second architecture center with competing
  names or stage ownership

Deliverables:

- written contracts for each product
- declared ordering and fingerprint rules
- rules for which layers may create or transform each product

Entry criteria:

- shared foundations and first-increment bridge mapping are stable enough that
  broader family migration will not re-open core contract questions

### Roadmap Phase R2. Split The Contract Into Facets

Replace the current bundled source adapter interface with a small set of
purpose-defined facets.

Planned facets:

- probe or discovery facet
- evidence reader facet
- statement facet
- semantic translator facet
- artifact writer facet

Goals:

- allow intake-only adapters to stay intake-only
- allow statement-capable adapters to declare only statement work
- keep writer adapters separate from semantic readers without duplicating the
  manifest model

Non-goals:

- preserving the current monolithic shape under new names
- adding wrappers that keep both contract systems alive indefinitely

### Roadmap Phase R3. Make Manifests Declarative

Move more behavior description into manifests instead of open-coded adapter
methods where the behavior is structural rather than semantic.

Candidate manifest-owned data:

- evidence family signatures
- accepted artifact kinds
- planner support and selection modes
- statement kinds
- ordering and serialization rules
- determinism guarantees
- schema version and compatibility rules
- supported claim and artifact types

Exit criteria:

- a reader can understand what an adapter can do from its manifest and small
  provider-local modules, not from a large composite entry point

### Roadmap Phase R4. Unify Verification Around Adapter Products

Build one verifier that checks the adapter products instead of relying on a
mix of adapter-local conventions.

Verifier goals:

- replay stability on unchanged inputs
- product fingerprint stability
- no unordered output surfaces
- explicit unsupported or ambiguous cases
- artifact parity where projections exist

Exit criteria:

- adapter verification is centered on adapter products and deterministic
  compiler behavior

### Roadmap Phase R5. Migrate Adapter Families In Priority Order

Once the future contracts exist, migrate adapter families in bounded phases.

Recommended order:

1. filing-critical platform adapters
2. filing-critical writer adapters
3. wallet and explorer adapters needed for checkpoint confidence
4. remaining supported platform adapters
5. generic and reserved surfaces

Rules:

- migrate one family at a time
- keep each migration checkpoint reviewable
- remove obsolete seams once the new family path is stable
- avoid a giant umbrella migration

### Roadmap Phase R6. Retire The Bundled Current Contract

Only after migrated families are stable should the repo remove the current
bundled contract shape.

Retirement conditions:

- no filing-critical adapter depends on the old contract
- verification has moved to adapter products
- docs, scaffolds, and tests all describe the new model

## Decision Rules While Filing Work Is Active

Use these rules to decide whether an adapter change belongs in `now` or
`prep` or `roadmap`.

Choose `now` when:

- the change directly improves a filing-critical adapter or output
- the change removes a current source of nondeterminism
- the change moves duplicated workflow logic into an already visible shared
  seam
- the change improves replay confidence on unchanged inputs
- the change makes unsupported or ambiguous behavior explicit

Choose `prep` when:

- the change freezes adapter products or bridge mapping required by Phase 0
- the change aligns current planner or translation seams with proto-
  `EvidenceSet` or proto-`ClaimSet`
- the change establishes shared ordering, fingerprint, or compatibility rules
- the change enables one bounded family slice without introducing wrapper lanes
- the change advances shared compiler or verifier seams needed by the first
  target-stage slice

Choose `roadmap` when:

- the change exists mainly to prepare a future interface
- the change introduces a new abstraction layer with no filing benefit
- the change requires dual-contract support or migration wrappers
- the change primarily benefits non-filing adapters
- the change expands stubs, reserved surfaces, or speculative future adapter
  kinds

When in doubt:

- prefer the smaller current-contract hardening change
- record the future design pressure in roadmap notes instead of solving it
  prematurely in code

## Relationship To The Roadmap

This plan does not replace `ROADMAP.md`.

`ROADMAP.md` should continue to track the long-range architecture sequence.
This document narrows one immediate execution question that the main roadmap
does not need to carry in detail:

- what adapter work should happen before taxes
- what adapter work should wait until after filing

The broad unified adapter redesign remains a roadmap item. The current filing
window should stabilize the path, not perfect the architecture.
