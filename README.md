# Crypto Reconciliation

Typed crypto ledger reconciliation tooling with a strict layered architecture
and an external workspace model.

This repository ships the `tallylot` library package and the `tallylot` CLI
entry point. The repo owns code, tests, docs, templates, and agent guidance.
Live evidence and operational artifacts belong in the external workspace.

## Principles

- Keep business logic in the typed package under `src/tallylot/`.
- Keep financial values in `Decimal`.
- Surface ambiguous or unsupported data as explicit issues.
- Keep repo docs and agent entrypoints aligned with the actual runtime.

## Scope

- Python `3.12`
- `uv` for environment and command execution
- CLI and library interfaces only in this phase
- filesystem-backed operational storage
- external workspace model

Use [docs/status/current-state.md](docs/status/current-state.md) for
the current implemented runtime surface.

## Documentation Map

- [ROADMAP.md](ROADMAP.md): remaining planned work and sequencing
- [CHANGELOG.md](CHANGELOG.md): completed mainline milestones
- [docs/README.md](docs/README.md): docs index and ownership map
- [docs/status/current-state.md](docs/status/current-state.md):
  current implemented runtime surface
- [docs/architecture/README.md](docs/architecture/README.md): architecture and
  implementation rules
- [docs/operations/README.md](docs/operations/README.md): operator workflows
  and artifact contracts
- [docs/workspace/README.md](docs/workspace/README.md): repo-owned guidance for
  external workspace subtrees
- [AGENTS.md](AGENTS.md): task routing for coding agents

## Workspace Model

Default workspace root:

```text
~/tallylot-workspace
```

Resolution order:

1. `CRYPTO_RECON_WORKSPACE_ROOT`
2. `tallylot.toml` `[workspace].root`
3. built-in default

Initialize a workspace with:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot workspace init
```

Use [docs/file-map.md](docs/file-map.md) for task-to-command routing and
[docs/guides/operator-quickstart.md](docs/guides/operator-quickstart.md)
for the shortest operator path.

## Development

This repo intentionally uses the external environment at
`$HOME/.venvs/tallylot-py312`. The repo-root `.venv` file is a sentinel, not a
virtualenv directory.

Common setup and verification commands:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv sync --python 3.12
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.install_git_hooks
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests
```

Use [docs/standards/implementation.md](docs/standards/implementation.md)
for coding-time rules and
[docs/standards/commits.md](docs/standards/commits.md)
for commit and PR policy.

## License

[MIT](LICENSE)
