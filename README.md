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
- generic file output rendering with the CoinTracking CSV adapter implemented
- archive-aware source scanning and intake planning/apply
- restored real source adapters for Coinbase, Wealthsimple, Binance,
  Crypto.com, Shakepay, Ledger Live, Near, GTrade, EVM explorer, EVM
  wallet-state, and the generic structured CSV adapter
- blockchain, platform API, SQLite, and provider-backed AI remain stubbed

## Workspace Model

Default workspace root:

```text
~/crypto-reconciliation-workspace
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
uv run crypto-reconciliation source manifest --source-dir <path> --output <path>
uv run crypto-reconciliation source intake plan --incoming-dir <path> --report-dir <path>
uv run crypto-reconciliation source intake apply --incoming-dir <path> --report-dir <path>
uv run crypto-reconciliation source profile --source <name> --raw-dir <path> --output-dir <path>
uv run crypto-reconciliation source normalize --source <name> --raw-dir <path> --output-dir <path>
uv run crypto-reconciliation checkpoint rebuild-wallet-inventory --normalized-root <path> --output <path>
uv run crypto-reconciliation checkpoint extract-pdf-balances --pdf <path> --output <path> --statement-kind <kind>
uv run crypto-reconciliation output render file --output-adapter cointracking_csv --facts <path> --output <path>
```

## Development

```bash
uv sync --python 3.12
uv run python -m tools.install_git_hooks
uv run pre-commit run markdownlint --all-files
uv run python -m tools.run_quality_gates
uv run python -m tools.run_quality_gates --full-tests
```

`markdownlint`, `ruff`, `mypy`, `pyright`, `pylint`, and `pytest` are all part
of the expected quality baseline.

Commit-time `pytest` hooks intentionally run only `unit and not slow` without
coverage so local commits stay responsive. Use the full `uv run pytest` command
for complete verification.

The installed `pre-commit` wrapper runs Ruff autofix and formatting on safe
staged Python files before the rest of the hook suite, then stages those
formatter edits automatically. Partially staged Python files are left alone.

The parallel quality-gate runner is the preferred explicit verification path.
Do not also run `uv run pre-commit run --all-files` unless you specifically
need to validate the hook wiring itself.

Benchmark test segments with:

```bash
uv run python -m tools.benchmark_tests
uv run python -m tools.benchmark_tests --parallel
uv run python -m tools.scaffold_adapter source platforms/example_exchange "Example Exchange"
uv run python -m tools.refresh_adapter_goldens --pack structured_csv/basic
```

Run local quality gates in parallel with:

```bash
uv run python -m tools.run_quality_gates
uv run python -m tools.run_quality_gates --full-tests
```

## Docs

Start with [AGENTS.md](AGENTS.md) for task routing, then use the repo-owned
docs under [docs/](docs/README.md). For the narrowest doc or command route,
use [docs/file-map.md](docs/file-map.md).

## License

[MIT](LICENSE)
