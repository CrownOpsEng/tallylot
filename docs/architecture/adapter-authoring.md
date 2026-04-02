# Adapter Authoring

Adapters are first-class modules inside the repo and are discovered
automatically.

## Rules

- Keep adapter metadata, code, and tests together.
- Implement the `SourceAdapter` or `OutputAdapter` port only.
- Keep adapters pure with respect to filesystem layout except for reading their
  assigned input paths.
- Keep adapter entry points small. If parsing, mapping, issue handling, or
  rendering logic starts to crowd a single file, convert the adapter into a
  package-style module and split those responsibilities explicitly.
- Do not hide adapter complexity in generic helper modules. Use adapter-local
  names that reflect the real job being done.
- Surface unsupported or ambiguous rows as issues rather than guessing.
- Use typed domain models as the adapter output contract.
- Normalize source-specific sign conventions at the adapter edge. Canonical
  `CanonicalEvent` amounts stay positive; direction belongs in the mapped
  fields, not signed magnitudes.

## Discovery

- Source adapters live under `crypto_reconciliation.adapters.sources`.
- Group source adapters by source kind first:
  - `generic/` for reusable source contracts such as structured CSV
  - `portfolio/` for portfolio-import surfaces such as CoinTracking exports
  - `explorers/` for blockchain explorer exports
  - `wallets/` for wallet-state and wallet-owned exports
  - `platforms/` for exchange or custodial platform exports
  - `stubs/` for reserved non-runtime entry points
- Output adapters live under `crypto_reconciliation.adapters.outputs`.
- Discovery scans category namespaces and adapter package entry points
  recursively.
- Package-style adapters should expose `ADAPTER` from `__init__.py` or
  `adapter.py`.
- Package-local helpers, fixtures, and tests are intentionally ignored by
  discovery.
- Discovery loads `ADAPTER` objects and validates their manifests.
- `pytest` should collect adapter-local tests from package-local `tests/`
  directories under `src/crypto_reconciliation/adapters/...`.

## Testing

- Each working adapter should have contract tests.
- High-risk mapping logic should have unit coverage.
- Keep adapter-owned unit coverage beside the adapter package. Shared registry,
  service, or tooling coverage that is not owned by one adapter should live
  under the repo-level `tests/` tree instead.
- When an adapter becomes materially more complex, add golden fixtures that
  assert normalized events, balances, issues, and rendered outputs.
- Adapters must continue to pass both strict type checkers. Do not rely on
  runtime tests as a substitute for `mypy` and `pyright`.

## Tooling

- Scaffold package-style adapters with
  `uv run python -m tools.scaffold_adapter source platforms/<module_name> "<Display Name>"`
  or `uv run python -m tools.scaffold_adapter output <module_name> "<Display Name>"`.
- Source scaffolds must include the category path so new adapters land in the
  correct namespace from the start.
- Refresh JSON golden fixtures with
  `uv run python -m tools.refresh_adapter_goldens --pack <adapter>/<pack>`.
- Keep pack manifests under `tests/fixtures/adapter_packs/<adapter>/<pack>/`.
- Treat the golden refresh tool as a typed-service workflow. Do not route new
  adapter goldens through removed legacy scripts.
