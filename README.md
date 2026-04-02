# TallyLot

TallyLot is a typed Python toolkit for source-backed transaction intake,
evidence handling, checkpoint workflows, output generation, and tax-oriented
processing. It keeps live operational artifacts in an external workspace and
keeps the repo focused on code, tests, docs, templates, and automation.

## What This Repo Includes

- the `tallylot` Python package under `src/tallylot/`
- the `tallylot` CLI entry point
- typed intake, normalization, checkpoint, output, and oracle-support workflows
- source and output adapter boundaries over a provider-neutral runtime model
- repo-owned docs, templates, automation, and agent guidance
- an external workspace model for evidence and operational artifacts

## Current Status

The current runtime is CLI- and library-only, filesystem-backed, and centered
on typed workflows that keep raw evidence outside the repo. See
[docs/status/current-state.md](docs/status/current-state.md) for the detailed
implemented surface.

## Highlights

- strict typed layering between domain, application, ports, infrastructure,
  adapters, and interfaces
- external workspace model that keeps live evidence and operator artifacts out
  of the repo
- deterministic artifact generation for manifests, normalization output,
  checkpoint output, and validation packages
- explicit issues for unsupported or ambiguous data
- provider-neutral transaction facts as the canonical runtime model
- adapter-driven source and output boundaries, with mirrored workspace guidance
  under [docs/workspace/README.md](docs/workspace/README.md)

## Quick Start

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv sync --python 3.12
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.install_git_hooks
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot workspace init
```

See:

- [docs/README.md](docs/README.md)
- [docs/guides/operator-quickstart.md](docs/guides/operator-quickstart.md)
- [AGENTS.md](AGENTS.md)

## Documentation

- [docs/README.md](docs/README.md)
- [docs/status/current-state.md](docs/status/current-state.md)
- [docs/guides/operator-quickstart.md](docs/guides/operator-quickstart.md)
- [docs/concepts/architecture-overview.md](docs/concepts/architecture-overview.md)
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

Bootstrap the clone and run the standard checks with:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.install_git_hooks
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
