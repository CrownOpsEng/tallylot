# Normalization Exceptions

Review these artifacts after `source normalize`:

- `exceptions.csv` for blocking or unsupported rows
- `normalization_reviews.csv` for explicit assumptions and canonicalizations
- `facts.csv` for the internal fact artifact set

If the issue is a candidate-shape or overlap problem, render a candidate with
`output render file` and continue with `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli batch screen`
rather than editing the candidate blindly.
