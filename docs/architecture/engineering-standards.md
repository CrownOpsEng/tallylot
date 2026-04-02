# Engineering Standards

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

If a change crosses layer boundaries, refactor the boundary instead of
importing through it.

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
  under test. Do not widen production visibility for tests; use narrow,
  tool-supported test-side exclusions instead.
- Prefer the smallest available exclusion scope:
  - repo config for broad test-only policy
  - per-file config when an entire test module needs an exception
  - line-level suppression when only one access or one diagnostic needs relief

## Modularization Rules

Default to one responsibility per module.

- Keep most modules under roughly 150 lines.
- Start a split review once a module approaches 200 lines.
- Refactor before extending beyond 300 lines unless the file is mostly
  declarative models, typed schemas, or protocol definitions.
- Treat `300` lines as the official repo refactor limit.
- Treat `450` lines as the hard-stop lint ceiling (`150%` of the repo limit).
- Refactor by bounded concept, not by arbitrary suffixes.
- Do not add new dumping-ground modules such as `helpers.py`, `utils.py`,
  `misc.py`, or another catch-all `common.py`.
- Existing generic modules should shrink over time, not absorb more unrelated
  behavior.

When a capability grows, split by stable seams:

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
  `adapter.py` or `__init__.py` entry point plus local parser, mapper, issue,
  and fixture modules.
- `infrastructure/`: host reusable primitives only when they are genuinely
  cross-capability concerns such as filesystem guards, serialization, workspace
  persistence, or composition-root wiring. Do not push application policy down
  here just to share code.

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
- Prefer specific names such as `csv_parser.py`, `balance_mapper.py`, or
  `issue_rules.py` over generic names.
- Match package structure to the architecture first and the external provider
  second.
- New core-domain and application names should avoid crypto-exclusive language
  unless the concept is genuinely adapter-local or asset-class-specific.
- Under `adapters/sources/`, group packages by source kind before the provider:
  `platforms/<provider>/`, `wallets/<provider>/`, `explorers/<provider>/`,
  `portfolio/<surface>/`, `generic/<contract>/`, or `stubs/<reserved>/`.
- Keep naming stable across implementation, tests, and adapter metadata.

## Refactor-First Hotspots

Split these modules before adding materially new behavior:

- `src/tallylot/application/intake/packages/resolution.py`
- `src/tallylot/adapters/sources/platforms/binance/adapter.py`
- `src/tallylot/adapters/sources/platforms/coinbase/adapter.py`

Preserve these shared-surface package seams instead of collapsing them back
into single modules:

- `src/tallylot/domain/transactions/`
- `src/tallylot/interfaces/cli/`
- `src/tallylot/infrastructure/discovery/adapters/`
