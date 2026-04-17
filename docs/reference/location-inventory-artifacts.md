---
title: "Location Inventory Outputs"
summary: "Reference for location inventory outputs and evidence rows."
doc_type: reference
audience: human
owner: repo
status: active
naming_scope: current_state
nav_order: 30
---

The aggregate location inventory is rebuilt from normalized per-source outputs.

## Generated Files

| File | Purpose |
| ---- | ------- |
| `location_inventory.csv` | One row per normalized location identifier |
| `location_inventory_evidence.csv` | Evidence rows showing where each identifier came from through shared flattened locator columns |
| `location_inventory_issues.csv` | Deterministic review items such as conflicting location IDs or missing evidence paths |
| `location_inventory_summary.json` | High-level counts for agents and scripts |

## Rebuild

```bash
make cli ARGS='checkpoint rebuild-location-inventory \
  --normalized-root <workspace>/working/normalized \
  --output <workspace>/analysis/inventory/location_inventory.csv'
```

`--output` must point outside the normalized tree. The service rejects aggregate
outputs inside the scanned input root so reruns stay deterministic.

## Review Rules

- Treat `location_inventory.csv` as the compact lookup table.
- Use `location_inventory_evidence.csv` when you need the supporting
  capture-scoped locator columns:
  `evidence_capture_uid`, `evidence_relative_path`,
  `evidence_archive_member_path`, `evidence_locator_kind`, and
  `evidence_anchor`.
- Review `location_inventory_issues.csv` before treating a newly discovered
  identifier as import-ready evidence.
- Fix upstream normalized inputs when evidence paths or identifier assignments
  are wrong. Do not hand-edit the aggregate outputs.
