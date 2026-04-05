---
title: "Balance Submission Packages"
summary: "Mirrored workspace guidance for operator-authored manual balance submission packages."
doc_type: reference
audience: both
owner: repo
status: active
related:
  - docs/reference/manual-balance-submission-artifacts.md
  - docs/workspace/working/supporting_artifacts/README.md
  - docs/workspace/working/normalized/README.md
---

This subtree mirrors the runtime path for manual balance submission packages:

- `working/supporting_artifacts/balance_submissions/<source>/`

These packages are operator- or agent-authored support artifacts. They are not
raw evidence and they are not themselves the canonical reconciliation inputs.

## Package Role

Use this subtree when balances need to be authored into a repo-owned package
before they can be validated and materialized into canonical runtime files.

The scaffold path creates:

- `README.md`
- `balances.csv.example`
- `balance_evidence.csv.example`
- `location_inventory.csv.example`

The filled submission package should then contain:

- `balances.csv`
- `balance_evidence.csv`
- `location_inventory.csv` when explicit location identity is available

## Submit Handoff

Run `checkpoint submit-balances` against the filled package to validate the
submission and materialize canonical outputs elsewhere, normally under
`working/normalized/<source>/`.

The submit workflow writes:

- canonical `balances.csv`
- canonical `balance_evidence.csv`
- canonical `location_inventory.csv` when present
- `balance_submission_summary.json`
- `balance_submission_issues.csv`

Keep the submission package and the canonical output tree separate. The submit
workflow rejects output paths inside the submission package tree.
