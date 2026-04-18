# Location Inventory

Rebuild the aggregate location inventory with:

```bash
make cli ARGS='checkpoint rebuild-location-inventory \
  --normalized-root <workspace>/working/normalized \
  --output <workspace>/analysis/inventory/location_inventory.csv'
```

Review:

- `location_inventory.csv`
- `location_inventory_evidence.csv`
- `location_inventory_issues.csv`
- `location_inventory_summary.json`
