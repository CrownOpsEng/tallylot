# Import Batches

Place the next approved import batch for a single source here.

In the current runtime, this is usually a CoinTracking-ready CSV candidate.
Keep the folder semantics tracker-agnostic even while the implemented operator
workflow still targets CoinTracking.

Every file here should have:

- an upstream raw source export
- a reviewed normalization path
- a passing `uv run python -m tools.oracles.cli batch screen` result saved beside the candidate
- a matching entry in the round log before import
