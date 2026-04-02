# Wallet Inventory Artifacts

This folder holds the aggregate wallet inventory rebuilt from normalized source
artifacts.

Files:

- `wallet_inventory.csv`
- `wallet_inventory_evidence.csv`
- `wallet_inventory_issues.csv`
- `wallet_inventory_summary.json`

Refresh with:

```bash
uv run crypto-reconciliation checkpoint rebuild-wallet-inventory \
  --normalized-root <workspace>/working/normalized \
  --output <workspace>/analysis/inventory/wallet_inventory.csv
```

Do not hand-edit the generated outputs. Fix the upstream normalized inputs and
rebuild.
