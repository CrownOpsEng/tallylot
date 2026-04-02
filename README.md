# Crypto Reconciliation

Typed crypto ledger reconciliation tooling with a strict layered architecture
and an external workspace model.

This repository ships the `tallylot` library package and the
`tallylot` CLI entry point. The repo owns code, tests, docs,
templates, and agent guidance. Live evidence and operational artifacts belong
in the external workspace.

## Principles

- Keep business logic in the typed package under `src/tallylot/`.
- Keep financial values in `Decimal`.
- Surface ambiguous or unsupported data as explicit issues.
- Keep repo docs and agent entrypoints aligned with the actual runtime.

## Runtime Model

- Python `3.12`
- `uv` for environment and command execution
- CLI and library interfaces only in this phase
- filesystem-backed operational storage
- generic file output rendering with the CoinTracking CSV adapter implemented
- archive-aware source scanning and intake planning/apply
- restored real source adapters for Coinbase, Wealthsimple, Binance,
  Crypto.com, Shakepay, Ledger Live, Near, GTrade, EVM explorer, EVM
  wallet-state, and the generic structured CSV adapter
- blockchain, platform API, SQLite, and provider-backed AI remain stubbed

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

## Commands

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot workspace init
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source manifest --source-dir <path> --output <path>
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source intake plan --incoming-dir <path> --report-dir <path>
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source intake apply --incoming-dir <path> --report-dir <path>
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source profile --source <name> --raw-dir <path> --output-dir <path>
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source normalize --source <name> --raw-dir <path> --output-dir <path>
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot checkpoint rebuild-wallet-inventory --normalized-root <path> --output <path>
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot checkpoint extract-pdf-balances --pdf <path> --output <path> --statement-kind <kind>
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot output render file --output-adapter cointracking_csv --facts <path> --output <path>
```

## Development

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv sync --python 3.12
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.install_git_hooks
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pre-commit run markdownlint --all-files
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests
```

This repo intentionally uses the external environment at
`$HOME/.venvs/tallylot-py312`. The repo-root `.venv` file is a sentinel, not a
virtualenv directory, so direct repo command examples should keep the explicit
`UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312"` prefix unless you set up
the Bash wrapper below.

For Bash, prefer a repo-scoped wrapper instead of a global export:

```bash
uv() {
    if [[ "$PWD" == "$HOME/Code/tallylot" || "$PWD" == "$HOME/Code/tallylot/"* ]]; then
        UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" command uv "$@"
        return
    fi

    command uv "$@"
}
```

After syncing an external environment, select its interpreter in your editor,
for example `~/.venvs/tallylot-py312/bin/python` in VS Code.

`markdownlint`, `ruff`, `mypy`, `pyright`, `pylint`, and `pytest` are all part
of the expected quality baseline.

Commit-time `pytest` hooks intentionally run only `unit and not slow` without
coverage so local commits stay responsive. Use the full
`UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pytest` command
for complete verification.

The installed `pre-commit` wrapper runs Ruff autofix and formatting on safe
staged Python files before the rest of the hook suite, then stages those
formatter edits automatically. Partially staged Python files are left alone.

The parallel quality-gate runner is the preferred explicit verification path.
Do not also run
`UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pre-commit run --all-files`
unless you specifically need to validate the hook wiring itself.

Benchmark test segments with:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.benchmark_tests
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.benchmark_tests --parallel
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.scaffold_adapter source platforms/example_exchange "Example Exchange"
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.refresh_adapter_goldens --pack structured_csv/basic
```

Run local quality gates in parallel with:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests
```

## Docs

Start with [AGENTS.md](AGENTS.md) for task routing, then use the repo-owned
docs under [docs/](docs/README.md). For the narrowest doc or command route,
use [docs/file-map.md](docs/file-map.md).

## License

[MIT](LICENSE)
