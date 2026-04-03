"""Workspace layout constants."""

from __future__ import annotations

from dataclasses import dataclass


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
        "issue_id,source,adapter_id,severity,kind,message,context_timestamp,raw_file,raw_row_ref,status\n",
    ),
    SeedFile(
        "analysis/issues/source_inventory.csv",
        "source,capture_path,status,notes\n",
    ),
    SeedFile(
        "analysis/inventory/wallet_inventory.csv",
        "wallet_id,source,account,wallet,evidence_path,identifier_kind,identifier_value,notes\n",
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
