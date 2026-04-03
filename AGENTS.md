# AGENTS.md

## Objective

Work with the user to repair and extend the CoinTracking ledger from the 2023-08-05 checkpoint through 2025-12-31 with minimum friction and no hidden corruption.

## System of record

CoinTracking.info is the live ledger. This repo is the evidence, staging, and verification workspace.

## Compliance foundation

Canadian tax compliance is foundational. When process convenience conflicts with CRA primary guidance or required books and records, the CRA-aligned treatment wins.

## Canonical baseline

- Baseline folder: `01_raw_exports/cointracking/2023-08-05_full_export/`
- Authoritative cutoff timestamp: `2023-08-05 08:34:04`
- Delta work starts strictly after that timestamp unless a newer baseline is intentionally adopted.

## Source priority

1. `01_raw_exports/cointracking/2023-08-05_full_export/`
2. Fresh post-repair CoinTracking exports captured in this repo
3. Raw external source exports under `01_raw_exports/external/`
4. Working derivatives in `02_working/`

## Non-negotiable rules

- Never overwrite raw exports.
- Never use stale loose exports outside the canonical full export folder for decisions.
- Never import multiple new sources into CoinTracking before verifying the previous source.
- Always log unresolved items in `03_analysis/issues/issue_log.csv`.
- Always keep `03_analysis/issues/source_inventory.csv` current before new source pulls.
- Always keep `03_analysis/inventory/wallet_inventory.csv` current after new wallet-app evidence or wallet-source profiling.
- Always update `05_outputs/logs/round_log.csv` after each repair or import round.
- Never auto-accept unexplained negative fiat balances as harmless; record or resolve them with evidence.
- Prefer the smallest efficient export set for repeated verification.
- Use heavy reports only when the light reports cannot explain a mismatch.

## Default verification export set

After any repair or source import, export:

- Validate Transactions
- Missing Transactions
- Duplicate Transactions
- Current Balance
- Balance by Exchange

Only add Trade Table, Roll Forward, or Double-entry when needed for root-cause analysis.

## AI role

AI should:

- compare fresh exports against prior state
- detect overlap / duplicate risk in import batches
- classify issues with evidence
- help reconcile changes after each import

AI should not:

- blindly relabel or delete transactions
- invent tax treatment
- assume transfer pairing without evidence

## Active control files

- `00_docs/BASELINE_VALIDATION.md`
- `03_analysis/issues/issue_log.csv`
- `03_analysis/issues/source_inventory.csv`
- `03_analysis/inventory/wallet_inventory.csv`
- `05_outputs/logs/round_log.csv`

## Repo-local AI workflows

- `07_skills/source-intake/`
- `07_skills/adapter-authoring/`
- `07_skills/normalization-exceptions/`
- `07_skills/round-verification/`
- `07_skills/wallet-inventory/`

Claude-compatible wrappers live under `.claude/commands/`.

## Success state

- Baseline issues resolved or documented with evidence
- All required source imports completed through 2025-12-31
- Verification package captured after each import round
- Final 2025 checkpoint archived in this repo
