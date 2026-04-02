# Crypto Reconciliation

Typed crypto ledger reconciliation tooling with a strict layered architecture
and an external workspace model.

This repository is MIT-licensed and ships both a library package,
`crypto_reconciliation`, and the `crypto-reconciliation` CLI entry point.

## Principles

- The repo contains application code, tests, docs, templates, and contracts.
- Live evidence and operational artifacts live in a configured external
  workspace, not inside the repo.
- The architecture is intentionally agent-friendly, but programmatic services
  remain the primary execution path.
- Financial records are handled with explicit types, `Decimal`, conservative
  defaults, and visible exception paths.

## Runtime Model

- Python `3.12`
- `uv` for environment and command execution
- `src/crypto_reconciliation/` as the single package root
- CLI and library interfaces only in this phase

## Package Layout

```text
src/crypto_reconciliation/
  domain/
  application/
  ports/
  infrastructure/
  adapters/
  interfaces/
```

## Workspace Model

The default workspace root is:

```text
~/Documents/CryptoLedgerWorkspaces/crypto-reconciliation-2025
```

Override order:

1. `CRYPTO_RECON_WORKSPACE_ROOT`
2. `crypto-reconciliation.toml` `[workspace].root`
3. built-in default

Initialize a workspace with:

```bash
uv run crypto-reconciliation workspace init
```

Repo-owned documentation stays under [`docs/`](docs/).
Versioned runbooks and templates live in the repo. The external workspace holds
live evidence, analysis artifacts, logs, and any working-copy docs under
`<workspace>/docs/`.

## Commands

```bash
uv run crypto-reconciliation workspace init
uv run crypto-reconciliation baseline validate --export-dir <path> --output-dir <path>
uv run crypto-reconciliation source manifest --source-dir <path> --output <path>
uv run crypto-reconciliation source profile --source <name> --raw-dir <path> --output-dir <path>
uv run crypto-reconciliation source normalize --source <name> --raw-dir <path> --output-dir <path>
uv run crypto-reconciliation wallet inventory rebuild --normalized-root <path> --output <path>
uv run crypto-reconciliation output render cointracking --canonical-events <path> --output <path>
uv run crypto-reconciliation verification compare --previous-dir <path> --current-dir <path> --output-dir <path>
uv run crypto-reconciliation batch stage --candidate <path> --baseline-export-dir <path> --output-dir <path>
```

## Installation

For local development:

```bash
uv sync --python 3.12
uv run crypto-reconciliation --help
```

To build distributable artifacts from a clean checkout:

```bash
uv build
```

Build artifacts are written to `dist/` and are ignored by git.

## Development

```bash
uv sync --python 3.12
git config --local commit.template .gitmessage.txt
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
uv run pre-commit run --all-files
uv run pre-commit run markdownlint --all-files
uv run ruff check .
uv run mypy
uv run pyright
uv run pylint src tests tools
uv run pytest
```

`markdownlint`, `ruff`, `mypy`, `pyright`, `pylint`, and `pytest` are all part
of the expected quality baseline. The repo already ships a
`.pre-commit-config.yaml`; install both the `pre-commit` and `commit-msg` hooks
and treat a passing hook run as the minimum commit baseline.

This repo uses a `src/` layout and expects editor diagnostics to run against the
project `.venv`. The checked-in VS Code workspace settings point Python,
Pylint, Mypy, and Ruff at that environment and add `src/` to analysis paths. If
diagnostics still show stale import errors after syncing, re-select the
workspace interpreter at `.venv/bin/python` and reload the VS Code window.

For AI-agent and contributor guardrails, start with `AGENTS.md` and then read
only the narrow doc needed for the task.

## License

[MIT](LICENSE)

## Docs

- [docs/README.md](docs/README.md)
- [ROADMAP.md](ROADMAP.md)
- [docs/commit-standards.md](docs/commit-standards.md)
- [docs/engineering-standards.md](docs/engineering-standards.md)
- [docs/workspace-layout.md](docs/workspace-layout.md)
- [docs/adapter-authoring.md](docs/adapter-authoring.md)
