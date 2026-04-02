# Wallet Inventory Artifacts

This folder holds generated wallet inventory artifacts.

Primary file:

- `wallet_inventory.csv`

Supporting evidence:

- `wallet_inventory_evidence.csv`
- `wallet_inventory_issues.csv`
- `wallet_inventory_summary.json`

Refresh with:

```bash
python3 06_scripts/wallet_inventory.py --repo-root .
```

Do not hand-edit the generated CSV or JSON files. Fix the raw capture, extraction logic, or source inventory instead, then regenerate.
