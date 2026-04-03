# Verification Packages

Create one folder per repair or import round.

Suggested folder names:

- `baseline_repair_round_01`
- `post_import_coinbase_01`

Each folder should contain the fresh verification export set captured
immediately after the related action.

For import rounds, also keep the
`uv run python -m tools.oracles.cli verification compare` output under a
subfolder such as `comparison/`.
