---
title: "Write An Adapter"
summary: "Rules, shape, testing, and tooling guidance for source and output adapters."
doc_type: guide
audience: human
owner: repo
status: active
nav_order: 60
---

Adapters are first-class modules inside the repo and are discovered
automatically.

## Rules

- Keep adapter metadata, code, and tests together.
- Implement the `SourceAdapter` or `OutputAdapter` port only.
- Keep the concrete adapter implementation class private inside `adapter.py` or
  `stub.py`, and publish the runtime entry point as the module-level `ADAPTER`
  instance from that implementation module.
- Keep adapters pure with respect to filesystem layout except for reading their
  assigned input paths.
- Treat source adapters as translation adapters, not orchestration centers.
- Prefer existing adapter support seams for stable cross-provider work such as
  file-family dispatch, CSV traversal, draft compilation, issue construction,
  wallet-record construction, and output projection so new adapters stay thin.
- Publish stable file-family ids from schema or content signatures before using
  filename or path hints. Translation code should consume those adapter-declared
  family ids rather than rediscovering provider filenames in each workflow.
- Keep shared support adapter-agnostic. It should work from registry-resolved
  manifests and adapter-published translation contracts, not from concrete
  provider ids hard-coded into support modules.
- Keep adapter entry points small. If parsing, mapping, issue handling, or
  rendering logic starts to crowd a single file, convert the adapter into a
  package-style module and split those responsibilities explicitly.
- Do not hide adapter complexity in generic helper modules. Shared support must
  live behind a specific adapter-layer seam, and provider-specific behavior
  must keep provider-local names that reflect the real job being done.
- Surface unsupported or ambiguous rows as issues rather than guessing.
- Use the shared adapter draft model as the source-translation contract.
- Pass layered classifications as domain enums through the shared draft model.
- Keep enum values machine-oriented and renderer-neutral; title-style labels
  belong only in output adapters or oracle-specific readers.
- Do not construct CoinTracking rows or other output-adapter payloads directly
  in provider-local modules.
- Do not synthesize runtime balance snapshots in adapters unless the source
  export provides actual balance evidence.
- Normalize source-specific sign conventions at the adapter edge into signed
  canonical quantities. If the provider sign or direction signal is ambiguous,
  surface an issue or review instead of guessing.
- Treat symbols, venue codes, and chain contracts as identifier inputs.
  Adapters should target canonical instrument references through the shared
  identifier-resolution seam rather than treating raw symbols as stable
  identity.
- Emit identifier claims that are sufficient for shared resolution to one
  canonical instrument. If resolution is unresolved or ambiguous, emit a review
  record plus a blocking issue and do not produce a fact for that activity.
- Use identifier-rooted canonical on-chain location ids:
  - EVM-family locations use `evm:<network>:<address>`
  - non-EVM chains use their own namespace such as `near:<account>` or
    `bitcoin:<address>`
  - derived sublocations append a stable suffix such as `:staking`
- Keep source labels, wallet names, and other friendly labels out of canonical
  runtime `location_id` values. Those labels belong in `source`,
  `location_label`, annotations, and output-adapter display logic.
- Normalize runtime timestamps at the adapter edge. Draft, fact, balance, and
  balance-evidence timestamps must be timezone-aware UTC before they enter the
  shared domain or port models.
- Declare numeric precision expectations at the adapter edge when the source
  contract depends on decimal scale for integrity. Use the shared decimal
  precision support to validate the fractional digits displayed in the raw
  source text, require exact or minimum scale as needed, allow explicit zero
  exemptions when appropriate, and surface rounded or truncated values as
  issues or reviews instead of silently accepting them.
- Preserve effective-time precision at the adapter edge. If the source provides
  only a date, emit date-only effective-time metadata. If the source provides an
  exact timestamp, preserve that exact timestamp even when it is midnight.
- Use the repo-wide temporal convention consistently. Fields that may be
  date-only or exact-time must use `*_at` plus `*_precision`, with one shared
  precision enum rather than provider-local boolean flags or ad hoc string
  markers.
- Infer temporal precision from the source contract and parsed field shape, not
  from the normalized clock value. An exact midnight timestamp remains
  `timestamp` precision; a date-only source value remains `date` precision.
- Declare `FactLegPolicy` explicitly on every emitted draft. Required kinds and
  zero-`primary` behavior must be expressed through the policy limits rather
  than inferred by shared defaults.

## Source Adapter Shape

Working source adapters should follow four steps:

1. parse provider exports into provider-local typed records
2. select a provider-local translation rule or grouped-operation rule
3. emit shared adapter drafts plus explicit issues or reviews
4. let shared compiler or projection support build runtime artifacts

The default source adapter package should keep:

- `adapter.py` for the thin port implementation and manifest
- a docstring-only package `__init__.py`; do not re-export `ADAPTER` from the
  package root
- `translation.py` for provider-local file-family or row translation registries
- optional provider-local parser modules and wallet-evidence modules

Provider-local translation code should convert provider timestamps to UTC-aware
runtime datetimes before draft construction and should publish any non-default
leg shape through explicit `LegShapeLimit` entries.

The core service should resolve the adapter through the registry and supply
only the minimal context the adapter needs to translate correctly. Export
families, translation registries, and provider-local coverage declarations come
from the adapter package itself, not from a support-layer provider table.

Mixed captures must fail explicitly. If profiling detects incompatible adapter
families in one raw source directory, the adapter should rely on the shared
blocking scan issue instead of attempting a best-effort normalization pass.

Wallet-state adapters must treat UI identity maps and friendly labels as labels
only. Emit canonical wallet inventory only when the export proves authoritative
chain-scoped or chain-specific ownership.

Known current adapter workaround:

- Ronin explorer `TxnFee(RON)` can round some historical-activity non-zero fees
  to six fractional digits even in newly downloaded CSV exports. Ronin
  therefore accepts non-zero fees only when the export exposes at least nine
  fractional digits, books those precise fees directly from CSV, and surfaces
  lower-precision non-zero values as explicit reviews while omitting the fee
  leg.

## Discovery

- Source adapters live under `tallylot.adapters.sources`.
- Group source adapters by source kind first:
  - `generic/` for reusable source contracts such as structured CSV
  - `portfolio/` for portfolio-import surfaces such as CoinTracking exports
  - `explorers/` for blockchain explorer exports
  - `wallets/` for wallet-state and wallet-owned exports
  - `platforms/` for exchange or custodial platform exports
  - `stubs/` for reserved non-runtime entry points
- Output adapters live under `tallylot.adapters.outputs`.
- Discovery scans category namespaces recursively and loads package
  implementation modules named `adapter.py` or `stub.py`.
- Package-style adapters should expose `ADAPTER` from `adapter.py` or `stub.py`,
  not from package `__init__.py` re-export shims.
- Package-local helpers, fixtures, and tests are intentionally ignored by
  discovery.
- Discovery loads `ADAPTER` objects and validates their manifests.
- `pytest` should collect adapter-local tests from package-local `tests/`
  directories under `src/tallylot/adapters/...`.

## Testing

- Each working adapter should have contract tests.
- High-risk mapping logic should have unit coverage.
- Add translation coverage tests for observed provider row kinds, file
  families, and grouped operations so missing cases fail explicitly.
- Keep adapter-owned unit coverage beside the adapter package. Shared registry,
  service, or tooling coverage that is not owned by one adapter should live
  under the repo-level `tests/` tree instead.
- Adapter-local tests that need implementation internals should import private
  adapter classes or helpers directly from `adapter.py`, `stub.py`, or the
  provider-local module under test. Do not add package-root re-export shims or
  widen production visibility for tests.
- When an adapter becomes materially more complex, add golden fixtures that
  assert transaction facts, balances, issues, and rendered outputs.
- Adapters must continue to pass both strict type checkers. Do not rely on
  runtime tests as a substitute for `mypy` and `pyright`.

## Tooling

- Scaffold package-style adapters with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.scaffold_adapter source platforms/<module_name> "<Display Name>"`
  or `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.scaffold_adapter output <module_name> "<Display Name>"`.
- Source scaffolds must include the category path so new adapters land in the
  correct namespace from the start.
- Scaffolds generate a private adapter implementation class, a module-level
  `ADAPTER` instance in `adapter.py`, a docstring-only package `__init__.py`,
  and package-local tests that import the private class directly from
  `adapter.py`.
- The scaffold tool refreshes `pyrightconfig.tests.json` so package-local
  adapter tests remain under the centralized test-private checker policy.
- Source scaffolds now generate `translation.py` with a provider-local
  `FILE_TRANSLATION_RULES` registry and a shared draft compiler call.
- Refresh JSON golden fixtures with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.refresh_adapter_goldens --pack <adapter>/<pack>`.
- Keep pack manifests under `tests/fixtures/adapter_packs/<adapter>/<pack>/`.
- Treat the golden refresh tool as a typed-service workflow. Do not route new
  adapter goldens through removed legacy scripts.
