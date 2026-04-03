---
name: wallet-inventory
description: Use when you need the canonical list of known wallet identifiers, need to reconcile an address back to its source evidence, or need to refresh and review wallet inventory artifacts before source intake or reconciliation work.
---

# Wallet Inventory

Use this skill when wallet identity is the question, not transaction classification.

## Default workflow

1. Read `03_analysis/inventory/wallet_inventory.csv` first.
2. If the needed identifier is missing or stale, run `06_scripts/wallet_inventory.py`.
3. Use `wallet_inventory_evidence.csv` to trace the identifier back to the raw file.
4. Review `wallet_inventory_issues.csv` before treating a partial alias or app-only discovery as import-ready evidence.
5. If a new source is being profiled, check the per-source wallet artifacts under `02_working/normalized/<source>/` as well.

## Guardrails

- Do not infer a full wallet address from a truncated alias without companion evidence.
- Do not treat app-wide wallet snapshots as a substitute for chain-scoped explorer exports.
- Prefer the generated inventory artifacts over reopening large raw exports unless the evidence row is insufficient.
- Keep the inventory DRY by updating extraction logic, not by hand-editing generated CSVs.

## Commands

```bash
python3 06_scripts/wallet_inventory.py --repo-root .
```
