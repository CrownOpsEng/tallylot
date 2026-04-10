---
title: "Wallet Inventory Artifacts"
summary: "Mirrored workspace contract for aggregate location inventory outputs and refresh commands."
doc_type: reference
audience: both
owner: repo
status: active
---

This folder holds the aggregate location inventory rebuilt from normalized source
artifacts.

Files:

- `source_captures.csv`
- `location_inventory.csv`
- `location_inventory_evidence.csv`
- `location_inventory_issues.csv`
- `location_inventory_summary.json`

`source_captures.csv` is the append-only capture registry keyed by
`capture_uid`. Each row records one lifecycle event for one capture, including
duplicate-blocked or excluded outcomes that never materialize a new raw capture
root. `location_inventory.csv` and the related evidence and issue artifacts
remain derived outputs rebuilt from normalized datasets.

`location_inventory_evidence.csv` carries the shared flattened provenance
locator family with `evidence_` prefixes:

- `evidence_capture_uid`
- `evidence_relative_path`
- `evidence_archive_member_path`
- `evidence_locator_kind`
- `evidence_anchor`

Those columns identify the supporting capture-scoped evidence row or document.
They replace ad hoc source-level path assumptions.

Refresh with:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot checkpoint rebuild-location-inventory \
  --normalized-root <workspace>/working/normalized \
  --output <workspace>/analysis/inventory/location_inventory.csv
```

Do not hand-edit the generated outputs. Fix the upstream normalized inputs and
rebuild.
