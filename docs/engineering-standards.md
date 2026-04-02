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
- Refactor before extending beyond 250 lines unless the file is mostly
  declarative models, typed schemas, or protocol definitions.
- Refactor by bounded concept, not by arbitrary suffixes.
- Do not add new dumping-ground modules such as `helpers.py`, `utils.py`,
  `misc.py`, or another catch-all `common.py`.
- Existing generic modules should shrink over time, not absorb more unrelated
  behavior.

When a capability grows, split by stable seams:

- `domain/`: separate models, value objects, and typed aliases by concept.
- `application/services/`: keep one workflow per service module; extract shared
  parsing, validation, or assembly logic into specifically named siblings.
  Once a workflow area grows beyond a few related siblings or starts building a
  flat pile of same-prefix modules such as `intake_*`, move it into a feature
  package such as `application/services/intake/`.
- `interfaces/`: keep command parsing and command execution thin; move real work
  into services.
- `adapters/`: move larger adapters to package-style modules with an
  `adapter.py` or `__init__.py` entry point plus local parser, mapper, issue,
  and fixture modules.

Mirror that structure in tests:

- place unit tests under the matching package path when a feature owns a
  package
- prefer `tests/unit/application/services/intake/...` over scattering
  `test_intake_*` files across unrelated directories

## Naming Rules

- Name modules after the bounded responsibility they own.
- Prefer specific names such as `csv_parser.py`, `balance_mapper.py`, or
  `issue_rules.py` over generic names.
- Match package structure to the architecture first and the external provider
  second.
- Keep naming stable across implementation, tests, and adapter metadata.

## Refactor-First Hotspots

Split these modules before adding materially new behavior:

- `src/crypto_reconciliation/application/services/intake.py`
- `src/crypto_reconciliation/application/services/intake_packages.py`
- `src/crypto_reconciliation/adapters/sources/binance/adapter.py`
- `src/crypto_reconciliation/adapters/sources/coinbase/adapter.py`
- `src/crypto_reconciliation/domain/models.py`
- `src/crypto_reconciliation/interfaces/cli.py`
- `src/crypto_reconciliation/infrastructure/discovery/adapters.py`
