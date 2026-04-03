# Wallet Inventory

Rebuild the aggregate wallet inventory with:

```bash
uv run tallylot checkpoint rebuild-wallet-inventory \
  --normalized-root <workspace>/working/normalized \
  --output <workspace>/analysis/inventory/wallet_inventory.csv
```

Review:

- `wallet_inventory.csv`
- `wallet_inventory_evidence.csv`
- `wallet_inventory_issues.csv`
- `wallet_inventory_summary.json`
