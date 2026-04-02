# Adapter Authoring

Adapters are first-class modules inside the repo and are discovered
automatically.

## Rules

- Keep adapter metadata, code, and tests together.
- Implement the `SourceAdapter` or `OutputAdapter` port only.
- Keep adapters pure with respect to filesystem layout except for reading their
  assigned input paths.
- Surface unsupported or ambiguous rows as issues rather than guessing.
- Use typed domain models as the adapter output contract.

## Discovery

- Source adapters live under `crypto_reconciliation.adapters.sources`.
- Output adapters live under `crypto_reconciliation.adapters.outputs`.
- Discovery only scans top-level adapter modules plus package entry points.
- Package-style adapters should expose `ADAPTER` from `__init__.py` or
  `adapter.py`.
- Package-local helpers, fixtures, and tests are intentionally ignored by
  discovery.
- Discovery loads `ADAPTER` objects and validates their manifests.

## Testing

- Each working adapter should have contract tests.
- High-risk mapping logic should have unit coverage.
- When an adapter becomes materially more complex, add golden fixtures that
  assert normalized events, balances, issues, and rendered outputs.
