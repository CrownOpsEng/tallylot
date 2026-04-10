---
title: "Manual Balance Submission Artifacts"
summary: "Reference contract for scaffolded manual balance submission packages and their canonical outputs."
doc_type: reference
audience: human
owner: repo
status: active
nav_order: 80
related:
  - docs/guides/normalize-screen-stage.md
  - docs/workspace/working/supporting_artifacts/balance_submissions/README.md
  - docs/workspace/analysis/reconciliation/README.md
---

Use this reference when a source's canonical balance artifacts need to come
from a validated manual submission package instead of directly from
normalization.

Manual submission confirms balances for runtime use. It does not create
source-backed evidence.

## Workflow

1. Run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot checkpoint scaffold-balance-submission --source <source>`.
2. Fill `balances.csv` and `balance_confirmations.csv`, and optionally
   `location_inventory.csv`, under
   `working/supporting_artifacts/balance_submissions/<source>/`.
3. Run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot checkpoint submit-balances --source <source>`.
4. Review `balance_submission_summary.json` and
   `balance_submission_issues.csv`.
5. If the submit run is not blocked, continue with:
   `reconciliation balances inspect`, `reconciliation balances check`, and
   `reconciliation balances summarize`.

The scaffold command creates only `README.md` and `.example` templates. It
does not create the filled CSVs.

## Submission Package Layout

Packages live under
`working/supporting_artifacts/balance_submissions/<source>/`.

Scaffolded files:

- `README.md`
- `balances.csv.example`
- `balance_confirmations.csv.example`
- `location_inventory.csv.example`

Operator-filled files:

- `balances.csv`
- `balance_confirmations.csv`
- `location_inventory.csv`

`.example` files are templates only. The submit workflow ignores them.

## Required And Optional Files

Required files:

- `balances.csv`
- `balance_confirmations.csv`

Optional file:

- `location_inventory.csv`

The user-facing schema does not require `location_id`. The submit workflow
derives canonical location identifiers from `source`, `account`, and `wallet`.

The user-facing schema does require `instrument_id`. The workflow preserves the
entered `instrument_id` exactly and does not infer it from symbols or labels.

## Exact Headers

### `balances.csv`

```text
source,account,wallet,instrument_id,quantity,as_of_at,as_of_precision,balance_kind,notes
```

Required fields:

- `source`
- `account`
- `wallet`
- `instrument_id`
- `quantity`
- `as_of_at`
- `as_of_precision`
- `balance_kind`

`notes` may be blank.

### `balance_confirmations.csv`

```text
source,account,wallet,instrument_id,quantity,as_of_at,as_of_precision,balance_kind,confirmation_kind,support_ref,asserted_meaning,reviewed_by,reviewed_at,reason,notes
```

Required fields are:

- `source`
- `account`
- `wallet`
- `instrument_id`
- `quantity`
- `as_of_at`
- `as_of_precision`
- `balance_kind`
- `confirmation_kind`
- `asserted_meaning`
- `reviewed_by`
- `reviewed_at`
- `reason`

Allowed `confirmation_kind` values:

- `external_support`
- `manual_assertion`

Conditional `support_ref` rules:

- `external_support` rows require a non-blank `support_ref`
- `manual_assertion` rows must leave `support_ref` blank

`notes` may be blank.

### `location_inventory.csv`

```text
source,account,wallet,identifier_kind,identifier_value,network_scope,controller,confidence,notes
```

If `location_inventory.csv` is present, these fields are required:

- `source`
- `account`
- `wallet`
- `identifier_kind`
- `identifier_value`
- `confidence`

`network_scope`, `controller`, and `notes` may be blank.

## Validation Behavior

The submit workflow is strict and deterministic.

- `balances.csv` and `balance_confirmations.csv` must exist as filled files.
- Headers must match exactly.
- Required fields must be non-blank.
- `quantity` must parse as `Decimal`.
- `as_of_at` and `as_of_precision` must form a valid persisted timestamp.
- `balance_kind` must normalize successfully.
- Duplicate logical balance rows block the run.
- Duplicate logical confirmation rows block the run.
- Every balance row must have exactly one matching confirmation row on
  `source`, `account`, `wallet`, `instrument_id`, `quantity`, `as_of_at`,
  `as_of_precision`, and `balance_kind`.
- Every confirmation row must match exactly one balance row on the same keys.
- `confirmation_kind` must be valid.
- `reviewed_at` must be a persisted timezone-aware timestamp.
- `support_ref` must follow the conditional rule above.
- If `location_inventory.csv` is present, conflicting high-confidence identity
  rows for the same logical location block the run.
- A blocked run still writes `balance_submission_summary.json` and
  `balance_submission_issues.csv`.

Fill the real CSVs only from explicit operator-reviewed source facts. Do not
infer missing identifiers, timestamps, quantities, support references, or
identity values.

## Instrument ID Examples

Acceptable `instrument_id` values include canonical identifiers such as:

- `symbol:BTC@coinbase`
- `symbol:ETH`
- `symbol:USDT`

The workflow validates only that `instrument_id` is present. It preserves the
entered value exactly in the canonical outputs.

## Canonical Outputs

By default, a successful submit run materializes canonical outputs under
`working/normalized/sources/<source>/`. The CLI also accepts an explicit output
directory as long as it is not inside the submission package tree.

Written files:

- `balances.csv`
- `balance_confirmations.csv`
- `location_inventory.csv` when the optional submission file is present
- `balance_submission_summary.json`
- `balance_submission_issues.csv`

These canonical files are the same runtime-facing artifacts that
`reconciliation balances inspect`, `reconciliation balances check`, and
`reconciliation balances summarize` consume.

Successful manual submission reports:

- `trust_tier` as `operator_confirmed`
- `ready_for_balance_check` as `true`
- `ready_for_source_backed_checkpoint` as `false`

Manual submission does not write canonical `balance_evidence.csv`.
`balance_evidence.csv` remains source-backed only.

Canonical `balance_confirmations.csv` uses the normalized header:

```text
source,location_id,instrument_id,quantity,as_of_at,as_of_precision,balance_kind,confirmation_kind,support_ref,asserted_meaning,reviewed_by,reviewed_at,reason,notes
```

## Corroboration Limits

Source-local balance checks work with `balances.csv` plus either
`balance_evidence.csv` or `balance_confirmations.csv`.

When both artifacts exist for the same balance key, source-backed
`balance_evidence.csv` wins and confirmations only fill uncovered keys.

Omitting `location_inventory.csv` limits cross-source corroboration because the
reconciliation workflow has less explicit location identity to compare across
sources. It does not prevent basic source-local balance assertion checks.

Cross-source corroboration still ignores `balance_confirmations.csv`.
Filing-ready checkpoint status still requires source-backed evidence.
