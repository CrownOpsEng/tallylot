"""README template rendering for manual balance submission packages."""

from __future__ import annotations


def render_balance_submission_readme(source: str) -> str:
    return f"""# Manual Balance Submission: {source}

This package holds a user-facing manual balance submission for `{source}`.

Required files:

- `balances.csv`
- `balance_evidence.csv`

Optional file:

- `location_inventory.csv`

Template files:

- `.example` files are templates only. Keep them as examples and copy their rows
  into real `.csv` files only when you have explicit facts to enter.

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
"""
