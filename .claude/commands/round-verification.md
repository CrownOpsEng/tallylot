# Round Verification

Use this route after a manual repair or import in the external verification tool.

1. `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli round scaffold`
2. save the fresh verification export set under `working/verification/<round_id>/`
3. `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli verification compare`
4. review the comparison package
5. update issue, source, and round-log records

Use `docs/operations/export-checklist.md` for the verification export set.
