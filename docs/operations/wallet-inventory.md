# Wallet Inventory

The aggregate wallet inventory is rebuilt from the normalized per-source wallet
artifacts.

## Generated Files

| File | Purpose |
| ---- | ------- |
| `wallet_inventory.csv` | One row per normalized wallet identifier |
| `wallet_inventory_evidence.csv` | Evidence rows showing where each identifier came from |
| `wallet_inventory_issues.csv` | Deterministic review items such as conflicting wallet IDs or missing evidence paths |
| `wallet_inventory_summary.json` | High-level counts for agents and scripts |

## Rebuild

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot checkpoint rebuild-wallet-inventory \
  --normalized-root <workspace>/working/normalized \
  --output <workspace>/analysis/inventory/wallet_inventory.csv
```

`--output` must point outside the normalized tree. The service rejects aggregate
outputs inside the scanned input root so reruns stay deterministic.

## Review Rules

- Treat `wallet_inventory.csv` as the compact lookup table.
- Use `wallet_inventory_evidence.csv` when you need the supporting capture path.
- Review `wallet_inventory_issues.csv` before treating a newly discovered
  identifier as import-ready evidence.
- Fix upstream normalized inputs when evidence paths or identifier assignments
  are wrong. Do not hand-edit the aggregate outputs.
