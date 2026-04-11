"""README template rendering for manual balance submission packages."""

from __future__ import annotations


def render_balance_submission_readme(source: str) -> str:
    return f"""# Manual Balance Submission: {source}

This package holds a user-facing manual balance submission for `{source}`.

Required files:

- `balance_snapshots.csv`
- `balance_references.csv`

Optional file:

- `location_inventory.csv`

Template files:

- `.example` files are templates only. Keep them as examples and copy their rows
  into real `.csv` files only when you have explicit facts to enter.
- do not create real submission CSVs until you have explicit user-provided facts
  for every required value.

Required data rules:

- `instrument_id` must be supplied explicitly. Do not guess or synthesize it
  from symbols, labels, or prior runs.
- The agent may copy template rows into real CSVs only from user-provided
  facts.
- Missing values must be resolved with the user, not guessed.

Corroboration note:

- `location_inventory.csv` is optional, but it improves cross-source
  corroboration when explicit identity data is available.
- Omitting `location_inventory.csv` still allows source-local balance checking
  after a successful submit.

Reference note:

- Manual submission writes `operator_assertion` rows into the shared balance
  reference artifact.
- `support_ref` is optional and may cite supporting material, but the row
  remains an operator assertion rather than a source-document reference.
- Successful manual submission prepares balance snapshots and operator
  assertions for runtime balance checks.
"""
