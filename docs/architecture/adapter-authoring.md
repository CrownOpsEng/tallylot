# Adapter Authoring

Adapters are first-class modules inside the repo and are discovered
automatically.

## Rules

- Keep adapter metadata, code, and tests together.
- Implement the `SourceAdapter` or `OutputAdapter` port only.
- Keep adapters pure with respect to filesystem layout except for reading their
  assigned input paths.
- Treat source adapters as translation adapters, not orchestration centers.
- Prefer existing adapter support seams for stable cross-provider work such as
  file-family dispatch, CSV traversal, draft compilation, issue construction,
  wallet-record construction, and output projection so new adapters stay thin.
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
- Normalize source-specific sign conventions at the adapter edge. Normalized
  fact-leg amounts stay positive; direction belongs in the mapped fields, not
  signed magnitudes.

## Source Adapter Shape

Working source adapters should follow four steps:

1. parse provider exports into provider-local typed records
2. select a provider-local translation rule or grouped-operation rule
3. emit shared adapter drafts plus explicit issues or reviews
4. let shared compiler or projection support build runtime artifacts

The default source adapter package should keep:

- `adapter.py` for the thin port implementation and manifest
- `translation.py` for provider-local file-family or row translation registries
- optional provider-local parser modules and wallet-evidence modules

The core service should resolve the adapter through the registry and supply
only the minimal context the adapter needs to translate correctly. Export
families, translation registries, and provider-local coverage declarations come
from the adapter package itself, not from a support-layer provider table.

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
- Discovery scans category namespaces and adapter package entry points
  recursively.
- Package-style adapters should expose `ADAPTER` from `__init__.py` or
  `adapter.py`.
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
- When an adapter becomes materially more complex, add golden fixtures that
  assert transaction facts, balances, issues, and rendered outputs.
- Adapters must continue to pass both strict type checkers. Do not rely on
  runtime tests as a substitute for `mypy` and `pyright`.

## Tooling

- Scaffold package-style adapters with
  `uv run python -m tools.scaffold_adapter source platforms/<module_name> "<Display Name>"`
  or `uv run python -m tools.scaffold_adapter output <module_name> "<Display Name>"`.
- Source scaffolds must include the category path so new adapters land in the
  correct namespace from the start.
- Source scaffolds now generate `translation.py` with a provider-local
  `FILE_TRANSLATION_RULES` registry and a shared draft compiler call.
- Refresh JSON golden fixtures with
  `uv run python -m tools.refresh_adapter_goldens --pack <adapter>/<pack>`.
- Keep pack manifests under `tests/fixtures/adapter_packs/<adapter>/<pack>/`.
- Treat the golden refresh tool as a typed-service workflow. Do not route new
  adapter goldens through removed legacy scripts.
