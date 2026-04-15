---
title: "Engineering Standards"
summary: "Code placement, typing, modularity, and naming rules for the typed application."
doc_type: standard
audience: human
owner: repo
status: active
nav_order: 10
---

Use this document for code-focused decisions only: placement, typing,
modularization, and naming.

## Layer Placement

Place code by responsibility, not by convenience:

- `domain/`: pure business models, value objects, enums, and shared typed
  aliases. No infrastructure, CLI, config-loader, filesystem, or network
  imports.
- `application/`: use-case orchestration, DTO assembly, and service logic over
  `domain` plus `ports`.
- `ports/`: `Protocol` contracts and narrow boundary types only.
- `infrastructure/`: implementations of `ports`, config loading, serialization,
  discovery, and workspace persistence details.
- `adapters/`: source and output adapters plus their adapter-local helpers.
- `interfaces/`: thin entry points such as the CLI. Interfaces orchestrate
  services; they do not own business rules.
- `repo_support/`: the current live shared support boundary for repo-native tooling
  and repo-side tests. Keep this outside `src/tallylot/` because it is not
  production/runtime code.

If a change crosses layer boundaries, refactor the boundary instead of
importing through it.

Repo-native support boundaries:

- `src/tallylot/` remains production/runtime code only.
- `tools/` remains the home for repo-native entry points and task-specific
  dev-only modules.
- `repo_support/` is the current live shared support boundary for repo-native tooling and
  repo-side tests.
- later implementation should rename that dev-only package area to `dev_support/`
  so the boundary is explicit.
- until that rename lands, `repo_support/` must stay narrow, typed,
  stdlib-first, and named by concept.
- do not let `repo_support/` become a generic catch-all while the repo is
  still on the current live name.

## Typing Rules

- Fully type all new and edited production code.
- Keep financial values in `Decimal`. Never introduce `float` for ledger or
  amount handling.
- Avoid `Any`. Only allow it at an unavoidable external boundary, then narrow
  it immediately.
- Annotate return types explicitly for public functions, service methods, and
  adapter entry points.
- Prefer typed DTOs, domain models, `Protocol`s, `Literal`s, and `NewType`s
  over loose `dict[str, object]` payloads.
- Model unsupported or ambiguous data as explicit issues or exceptions rather
  than widening types until everything fits.
- Tests inherit a narrower exception in `mypy` config, but test helpers should
  still stay typed unless doing so adds no value.
- Tests may exercise private helpers when the internal behavior is the thing
  under test. Import the private implementation directly from the module that
  owns it. Do not add package-root re-export shims, wrapper aliases, or widened
  production visibility for tests; use narrow, tool-supported test-side
  exclusions instead.
- Prefer the smallest available exclusion scope:
  - repo config for broad test-only policy
  - per-file config when an entire test module needs an exception
  - line-level suppression when only one access or one diagnostic needs relief

## Modularization Rules

Default to one responsibility per module.

- Keep most modules under roughly 300 lines.
- Start a split review once a module approaches 400 lines.
- Refactor before extending beyond 500 lines unless the file is mostly
  declarative models, typed schemas, or protocol definitions.
- Treat `500` lines as the official repo refactor limit.
- Enforced limit is `600` lines as the hard-stop lint ceiling.
- Keep the repo standard tighter than the enforcement ceiling so refactor
  expectations stay ahead of the hard-stop lint cap.
- Refactor by bounded concept, not by arbitrary suffixes.
- Do not add new dumping-ground modules such as `helpers.py`, `utils.py`,
  `misc.py`, or another catch-all `common.py`.
- Existing generic modules should shrink over time, not absorb more unrelated
  behavior.
- Apply the same rule to the current live `repo_support/` package area and the
  later target `dev_support/` package area. Shared repo-only support must be
  split by named boundaries, not collected under generic support modules.

When a capability grows, split by stable boundaries:

- `domain/`: separate models, value objects, and typed aliases by concept.
- `application/`: organize by bounded capability packages such as
  `application/intake/`, `application/profiling/`, `application/normalization/`,
  `application/checkpoints/`, and `application/outputs/`. Keep request and
  response contracts in capability-local `contracts.py` files and keep
  orchestration entry points in explicitly named use-case modules such as
  `build_profile.py`, `normalize_source.py`, or `render_output.py`.
- `interfaces/`: keep command parsing and command execution thin; move real work
  into application use cases.
- `adapters/`: move larger adapters to package-style modules with an
  `adapter.py` entry point, a docstring-only package `__init__.py`, and local
  parser, mapper, issue, and fixture modules.
- `infrastructure/`: host reusable primitives only when they are genuinely
  cross-capability concerns such as filesystem guards, serialization, workspace
  persistence, or composition-root wiring. Do not push application policy down
  here just to share code.
- `repo_support/`: host reusable repo-only support only when it is shared by
  multiple repo-native areas such as `tools/` and `tests/`. This is the
  current live name for a later `dev_support/` target. Do not move
  production/runtime concerns here.

Mirror that structure in tests:

- place unit tests under the matching package path when a feature owns a
  package
- prefer `tests/unit/application/intake/...` over scattering
  `test_intake_*` files across unrelated directories

### Package Escalation Rules

Do not keep flattening files forever once a feature package exists.

- Use a feature package when a flat layer directory would otherwise collect
  more than 2 same-prefix files for one capability.
- Treat this as a hard refactor trigger, not a style preference. The third
  same-prefix sibling is the trigger. Regroup the capability in the same task
  instead of leaving a flat prefix cluster behind.
- Inside an existing feature package, create a nested subpackage when one
  bounded sub-capability meets any of these conditions:
  - 3 or more files share the same concept or repeated prefix
  - the cluster has its own models, decision rules, and entry point
  - the tests naturally group under that sub-capability rather than under the
    parent feature as a whole
- Do not create a nested package on the first split. Keep 2 tightly related
  files flat unless they already represent a stable subdomain.
- Prefer one clear level of nesting over long flat prefixes. `intake/packages/`
  is better than `intake/package_*.py` once the package-rule cluster becomes a
  subsystem.
- Prefer at most 2 package levels below the layer root unless a deeper tree is
  clearly justified by external contracts or provider boundaries.

Current application of this rule:

- `application/intake/` is the correct top-level feature package for intake.
- `application/profiling/` is the correct top-level feature package for source
  profiling workflows and profile artifact helpers.
- `intake/packages/`, `intake/archive/`, `intake/file_facts/`, and
  `intake/routing/` are the correct nested packages for the intake subdomains
  that now own their own models, rules, and entry points.
- `intake/plan/` is the correct nested package for intake planning workflows,
  planned-item models, review assembly, and report rendering.
- Normalization window and derived-balance helpers belong under
  `application/normalization/` rather than as nearby flat siblings.
- Output rendering belongs under `application/outputs/`; CoinTracking is one
  output adapter, not an application-center compatibility lane.
- Dev-only oracle tooling must live outside `src/tallylot/`.

## Naming Rules

- Name modules after the bounded responsibility they own.
- Keep public names and commands simple, neutral, and ergonomic. Prefer short
  names that match the user-visible operation over long implementation labels,
  and only add qualifiers when a real naming collision or ambiguity exists.
- For domain and contract surfaces, prefer the shortest accurate noun phrase.
  Cut migration, workflow, or implementation adjectives before cutting the
  owning noun that tells readers what the thing is.
- Follow the same naming approach for modules, functions, classes, and commands:
  choose concise descriptive names over decorative jargon.
- Reject verbose pattern-label suffixes such as `UseCase`, `Manager`, or
  `Handler` unless they disambiguate a real collision in the surrounding
  namespace.
- Reserve suffixes precisely:
  - `Ref` for canonical identity tuples or stable pointers
  - `Id` and `*_id` for stable identifiers only
  - `Record` for persisted kernel families
  - `Explanation` for explanatory sidecars keyed to one kernel or support record
  - `Projection` and `Sidecar` for derived or compatibility outputs
- Prefer concrete owning nouns over abstract containers. Avoid names such as
  `Core`, `Data`, `Info`, `Context`, `Payload`, or `Item` when `Record`,
  `Explanation`, `Projection`, or the domain noun would say what the surface
  actually holds.
- Keep record-family stems and id stems aligned. Prefer `GapRecord` plus
  `gap_id` or `ReadinessRecord` plus `readiness_id` over longer names that
  repeat context the record family already supplies, unless a real sibling
  family would make the shorter stem ambiguous.
- Fingerprints are scalar values, not refs. Use `*_fingerprint` for stored
  fingerprints and reserve `*_ref` for product ids, record ids, tuple refs, or
  other explicit pointer shapes.
- Prefer `*_kind` for canonical one-of vocab and variant fields. Reserve
  `family` for prose grouping of related record types, adapters, or artifact
  lines rather than for kernel field names.
- Do not encode nullability in canonical target field names. Use the base noun
  or ref name and state optionality in the field contract rather than in
  suffixes that spell out nullability.
- Do not encode canonical ordering or record-local support role in a target
  field name when the enclosing contract already provides that meaning.
  Drop redundant ordering prefixes and contextual support adjectives when the
  record already establishes the relationship.
- Prefer `*_key` for stable discriminators inside canonical ids, tuples, and
  record-local identity seams. Avoid more abstract labels such as `*_anchor`
  or redundant labels such as `*_discriminator` when the field simply holds
  the stable key for that parent scope.
- Prefer the base noun when a field already stores the locator or ref itself.
  Avoid extra suffixes such as `_identity` when `member_locator` or
  `valuation_source_ref` already says what the value holds.
- For compatibility-only material that is not a target concept, name it by
  boundary and role rather than promoting it to a pseudo-domain type.
  Prefer `bridge annotation payload`, `output note sidecar`, or
  `compatibility sidecar` over introducing a new canonical-seeming type name in
  forward-looking docs or code.
- Name the held thing separately from its identity seam or persistence shell:
  `BasisPool` is a concept, `BasisPoolRef` is its ref, and
  `BasisTransitionRecord` is a kernel row family.
- Prefer specific names such as `csv_parser.py`, `balance_mapper.py`, or
  `issue_rules.py` over generic names.
- Match package structure to the architecture first and the external provider
  second.
- New core-domain and application names should avoid crypto-exclusive language
  unless the concept is genuinely adapter-local or asset-class-specific.
- Do not bake migration qualifiers such as `bridge`, `legacy`, `current`, or
  `compat` into canonical target-layer concepts, helper ids, or product ids
  unless the name is intentionally current-state or adapter-local.
- Under `adapters/sources/`, group packages by source kind before the provider:
  `platforms/<provider>/`, `wallets/<provider>/`, `explorers/<provider>/`,
  `portfolio/<input_kind>/`, `generic/<contract>/`, or `stubs/<reserved>/`.
- Keep naming stable across implementation, tests, adapter metadata, and owner
  docs.

## Refactor-First Hotspots

Split these modules before adding materially new behavior:

- `src/tallylot/application/intake/packages/resolution.py`
- `src/tallylot/adapters/sources/platforms/binance/adapter.py`
- `src/tallylot/adapters/sources/platforms/coinbase/adapter.py`

Preserve these shared package boundaries instead of collapsing them back
into single modules:

- `src/tallylot/domain/transactions/`
- `src/tallylot/interfaces/cli/`
- `src/tallylot/infrastructure/discovery/adapters/`
