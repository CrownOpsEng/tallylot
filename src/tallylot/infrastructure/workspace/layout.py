"""Workspace layout constants."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.ports.captures import SOURCE_CAPTURE_HEADER, SOURCE_INVENTORY_HEADER
from tallylot.ports.evidence import LOCATION_INVENTORY_HEADER


@dataclass(frozen=True)
class SeedFile:
    relative_path: str
    content: str


WORKSPACE_DIRECTORIES = (
    "analysis/inventory",
    "analysis/issues",
    "analysis/reconciliation",
    "config",
    "docs",
    "evidence/raw/portfolio",
    "evidence/raw/source",
    "outputs/checkpoints",
    "outputs/logs",
    "outputs/reports",
    "working/import_batches",
    "working/normalized",
    "working/supporting_artifacts",
    "working/verification",
)

SEED_FILES = (
    SeedFile(
        "analysis/issues/issue_log.csv",
        (
            "issue_id,source_file,issue_class,priority,asset,exchange,date,direction,amount,"
            "cad_value,status,disposition,likely_meaning,proof_needed,proof_path,"
            "proof_summary,planned_action,external_action,verification_path,gate_result,"
            "closed_at,notes\n"
        ),
    ),
    SeedFile(
        "analysis/issues/source_inventory.csv",
        ",".join(SOURCE_INVENTORY_HEADER) + "\n",
    ),
    SeedFile(
        "analysis/inventory/source_captures.csv",
        ",".join(SOURCE_CAPTURE_HEADER) + "\n",
    ),
    SeedFile(
        "analysis/issues/source_label_map.csv",
        "incoming_capture_scope,incoming_path_prefix,source,notes\n",
    ),
    SeedFile(
        "analysis/inventory/location_inventory.csv",
        ",".join(LOCATION_INVENTORY_HEADER) + "\n",
    ),
    SeedFile(
        "outputs/logs/round_log.csv",
        (
            "round_id,phase,source,date,goal,output_change,exports_captured,"
            "issues_opened_or_closed,gate_result,next_action\n"
        ),
    ),
    SeedFile(
        "config/workspace.json",
        '{\n  "workspace_initialized": true,\n  "schema_version": 1\n}\n',
    ),
    SeedFile(
        "docs/README.md",
        "# Workspace\n\nThis external workspace stores evidence and operational artifacts.\n",
    ),
)
