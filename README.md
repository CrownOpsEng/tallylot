# Crypto Reconciliation

Typed crypto ledger reconciliation tooling with a strict layered architecture
and an external workspace model.

This repository ships the `crypto_reconciliation` library package and the
`crypto-reconciliation` CLI entry point. The repo owns code, tests, docs,
templates, and agent guidance. Live evidence and operational artifacts belong
in the external workspace.

## Principles

- Keep business logic in the typed package under `src/crypto_reconciliation/`.
- Keep financial values in `Decimal`.
- Surface ambiguous or unsupported data as explicit issues.
- Keep repo docs and agent entrypoints aligned with the actual runtime.

## Runtime Model

- Python `3.12`
- `uv` for environment and command execution
- CLI and library interfaces only in this phase
- filesystem-backed operational storage
- CoinTracking CSV as the implemented output target
- structured CSV as the working source adapter in this package
- blockchain, platform API, SQLite, and provider-backed AI remain stubbed

## Workspace Model

Default workspace root:

```text
~/Documents/CryptoLedgerWorkspaces/crypto-reconciliation-2025
```

Resolution order:

1. `CRYPTO_RECON_WORKSPACE_ROOT`
2. `crypto-reconciliation.toml` `[workspace].root`
3. built-in default

Initialize a workspace with:

```bash
uv run crypto-reconciliation workspace init
```

## Commands

```bash
uv run crypto-reconciliation workspace init
uv run crypto-reconciliation baseline validate --export-dir <path> --output-dir <path>
uv run crypto-reconciliation source manifest --source-dir <path> --output <path>
uv run crypto-reconciliation source profile --source <name> --raw-dir <path> --output-dir <path>
uv run crypto-reconciliation source normalize --source <name> --raw-dir <path> --output-dir <path>
uv run crypto-reconciliation source reconcile --candidate <path> --reference <path> --output-dir <path>
uv run crypto-reconciliation wallet inventory rebuild --normalized-root <path> --output <path>
uv run crypto-reconciliation output render cointracking --canonical-events <path> --output <path>
uv run crypto-reconciliation verification compare --previous-dir <path> --current-dir <path> --output-dir <path>
uv run crypto-reconciliation batch screen --candidate <path> --baseline-export-dir <path> --output-dir <path>
uv run crypto-reconciliation batch stage --candidate <path> --baseline-export-dir <path> --output-dir <path>
uv run crypto-reconciliation round scaffold --round-id <id> --phase <phase> --source <source>
uv run crypto-reconciliation supporting extract-pdf-balances --pdf <path> --output <path> --statement-kind <kind>
```

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
of the expected quality baseline.

Commit-time `pytest` hooks intentionally run only `unit and not slow` without
coverage so local commits stay responsive. Use the full `uv run pytest` command
for complete verification.

Benchmark test segments with:

```bash
uv run python -m tools.benchmark_tests
uv run python -m tools.benchmark_tests --parallel
```

## Docs

Start with [AGENTS.md](AGENTS.md) for task routing, then use the repo-owned
docs under [docs/](docs/README.md).

## License

[MIT](LICENSE)
