# Crypto Reconciliation

Typed crypto reconciliation, checkpointing, journal output, and tax computation
tooling built on a strict layered architecture and an external workspace model.

## What This Repo Includes

- the `tallylot` Python package under `src/tallylot/`
- the `tallylot` CLI entry point
- provider-neutral fact, reconciliation, checkpoint, and output workflows
- repo-owned docs, templates, automation, and agent guidance
- an external workspace model for evidence and operational artifacts

## Current Status

The current runtime is CLI- and library-only, filesystem-backed, and centered
on typed workflows that keep raw evidence outside the repo. See
[docs/status/current-state.md](docs/status/current-state.md) for the detailed
implemented surface.

## Highlights

- strict typed layering with explicit boundaries between domain, application,
  ports, infrastructure, adapters, and interfaces
- `Decimal`-only financial handling
- provider-neutral transaction facts as the canonical runtime model
- explicit issues for unsupported or ambiguous data
- mirrored workspace guidance under [docs/workspace/README.md](docs/workspace/README.md)
- CoinTracking kept at the edge as an output adapter and oracle family

## Quick Start

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv sync --python 3.12
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.install_git_hooks
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot workspace init
```

See [docs/guides/operator-quickstart.md](docs/guides/operator-quickstart.md)
for the shortest workflow path and [docs/README.md](docs/README.md) for the
human docs homepage.

## Documentation

- [docs/README.md](docs/README.md)
- [docs/status/current-state.md](docs/status/current-state.md)
- [docs/guides/operator-quickstart.md](docs/guides/operator-quickstart.md)
- [docs/concepts/reconciliation-tax-architecture.md](docs/concepts/reconciliation-tax-architecture.md)
- [docs/standards/engineering.md](docs/standards/engineering.md)
- [AGENTS.md](AGENTS.md)

## Repository Layout

```text
src/
tests/
docs/
.claude/commands/
tools/
README.md
AGENTS.md
ROADMAP.md
CHANGELOG.md
```

## Development

This repo intentionally uses the external environment at
`$HOME/.venvs/tallylot-py312`. The repo-root `.venv` file is a sentinel, not a
virtualenv directory.

Common verification commands:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests
```

Use [docs/standards/implementation.md](docs/standards/implementation.md) and
[docs/standards/commits.md](docs/standards/commits.md) for repo execution and
checkpoint rules.

## Contributing

Use the standards docs for repo rules and [ROADMAP.md](ROADMAP.md) for active
sequencing:

- [docs/standards/engineering.md](docs/standards/engineering.md)
- [docs/standards/implementation.md](docs/standards/implementation.md)
- [docs/standards/commits.md](docs/standards/commits.md)

## License

[MIT](LICENSE)

## Security

Do not commit private workspace data, oracle bundles, or personal exports to
the repo.
