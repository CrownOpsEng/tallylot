# Import Batches

Place the next approved import batch for a single source here.

In the current runtime, this is usually an approved external-import artifact.
Keep the folder semantics generic even when a round uses one concrete adapter.

Every file here should have:

- an upstream raw source export
- a reviewed normalization path
- a passing `uv run python -m tools.oracles.cli batch screen` result saved beside the candidate
- a matching entry in the round log before import
