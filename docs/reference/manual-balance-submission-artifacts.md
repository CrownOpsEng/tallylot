---
title: "Manual Balance Submission Packages"
summary: "Reference for scaffolded manual balance submission packages and their balance outputs."
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

Use this reference when a source needs a validated manual submission package to
materialize balance outputs.

Manual submission is a checkpoint-owned input path. It produces
`balance_snapshots.csv` and `balance_references.csv` rows for runtime balance
checks, but it does not create document evidence on its own.

## Workflow

1. Run `make cli ARGS='checkpoint scaffold-balance-submission --source <source>'`.
2. Fill `balance_snapshots.csv` and `balance_references.csv`, and optionally
   `location_inventory.csv`, under
   `working/supporting_artifacts/balance_submissions/<source>/`.
3. Run `make cli ARGS='checkpoint submit-balances --source <source>'`.
4. Review `balance_submission_summary.json`. When the submit run has issues,
   review `balance_submission_issues.csv` as well.
5. If the submit run is not blocked, continue with
   `reconciliation balances inspect`, `reconciliation balances check`, and
   `reconciliation balances summarize`.

The scaffold command creates only `README.md` and `.example` templates. It
does not create the filled CSVs.

## Submission Package Layout

Packages live under
`working/supporting_artifacts/balance_submissions/<source>/`.

Scaffolded files:

- `README.md`
- `balance_snapshots.csv.example`
- `balance_references.csv.example`
- `location_inventory.csv.example`

Operator-filled files:

- `balance_snapshots.csv`
- `balance_references.csv`
- `location_inventory.csv`

`.example` files are templates only. The submit workflow ignores them.

## Required And Optional Files

Required files:

- `balance_snapshots.csv`
- `balance_references.csv`

Optional file:

- `location_inventory.csv`

The user-facing schema does not require `location_id`. The submit workflow
derives location identifiers from `source`, `account`, and `wallet`.

The user-facing schema does require `instrument_id`. The workflow preserves the
entered `instrument_id` exactly and does not infer it from symbols, labels, or
prior runs.

## Exact Headers

### `balance_snapshots.csv`

```text
source,account,wallet,instrument_id,quantity,target_at,target_precision,balance_kind,notes
```

Required fields:

- `source`
- `account`
- `wallet`
- `instrument_id`
- `quantity`
- `target_at`
- `target_precision`
- `balance_kind`

`notes` may be blank.

### `balance_references.csv`

```text
source,account,wallet,instrument_id,quantity,target_at,target_precision,balance_kind,reference_kind,observed_at,observed_precision,support_ref,reviewed_by,reviewed_at,notes
```

Required fields:

- `source`
- `account`
- `wallet`
- `instrument_id`
- `quantity`
- `target_at`
- `target_precision`
- `balance_kind`
- `reference_kind`
- `observed_at`
- `observed_precision`
- `reviewed_by`
- `reviewed_at`

Manual submission accepts only:

- `reference_kind=operator_assertion`

`support_ref` is optional. When present, it cites supporting material for the
operator assertion; it does not change the row into a source-document
reference.

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

- `balance_snapshots.csv` and `balance_references.csv` must exist as filled
  files.
- Headers must match exactly.
- Rows must not include extra values beyond the declared header.
- Required fields must be non-blank.
- `quantity` must parse as `Decimal`.
- `target_at` and `target_precision` must form a valid persisted temporal
  value.
- `balance_kind` must normalize successfully.
- Duplicate logical snapshot rows block the run. The logical key is
  `source`, `account`, `wallet`, `instrument_id`, `target_at`,
  `target_precision`, and `balance_kind`.
- Duplicate logical reference rows block the run. The logical key is
  `source`, `account`, `wallet`, `instrument_id`, `target_at`,
  `target_precision`, and `balance_kind`.
- Every snapshot row must have exactly one matching reference row on
  `source`, `account`, `wallet`, `instrument_id`, `quantity`, `target_at`,
  `target_precision`, and `balance_kind`.
- Every reference row must match exactly one snapshot row on the same keys.
- `reference_kind` must be valid and must be `operator_assertion`.
- `observed_at` and `observed_precision` must form a valid persisted temporal
  value.
- `reviewed_at` must be a valid persisted timestamp.
- If `location_inventory.csv` is present, conflicting high-confidence identity
  rows for the same logical location block the run.
- A blocked run still writes `balance_submission_summary.json` and
  `balance_submission_issues.csv`.

Fill the real CSVs only from explicit operator-reviewed facts. Do not infer
missing identifiers, timestamps, quantities, support references, or identity
values.

## Materialized Outputs

By default, a successful submit run materializes balance outputs under
`working/normalized/sources/<source>/`. The CLI also accepts an explicit output
directory as long as it is not inside the submission package tree.

Written files:

- `balance_snapshots.csv`
- `balance_references.csv`
- `location_inventory.csv` when the optional submission file is present
- `balance_submission_summary.json`
- `balance_submission_issues.csv` when validation finds issues

Successful submission reports:

- `ready_for_balance_check=true`
- `wrote_balance_snapshots=true`
- `wrote_balance_references=true`

Manual submission writes `operator_assertion` rows into the shared unified
reference artifact. It does not create `source_document` evidence or satisfy a
filing-ready evidence-backed checkpoint on its own.

## Corroboration Limits

Source-local balance checks work from derived balance targets and the selected
rows in `balance_references.csv`.

When stronger references exist for the same balance target, the shared
selection policy prefers:

1. `source_document`
2. `network_api`
3. `operator_assertion`

Omitting `location_inventory.csv` limits cross-source corroboration because the
reconciliation workflow has less explicit location identity to compare across
sources. It does not prevent source-local balance checks.
