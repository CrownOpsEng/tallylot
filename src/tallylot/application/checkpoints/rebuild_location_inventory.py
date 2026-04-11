"""Rebuild checkpoint-supporting location inventory aggregates."""

from __future__ import annotations

from pathlib import Path

from tallylot.application.checkpoints.contracts import (
    LocationInventoryRequest,
    LocationInventoryResponse,
)
from tallylot.application.checkpoints.location_inventory_summary import (
    summarize_location_inventory,
)
from tallylot.application.resource_refs import path_from_ref
from tallylot.application.workspace.filesystem import (
    ensure_output_not_within_input_tree,
    iter_tree_files,
)
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import EVIDENCE_PROVENANCE_HEADER

INVENTORY_HEADER = (
    "location_id",
    "location_kind",
    "location_label",
    "parent_location_id",
    "location_path",
    "identifier_kind",
    "normalized_identifier",
    "display_identifier",
    "network_scopes",
    "source_labels",
    "controller_labels",
    "parent_location_labels",
    "evidence_count",
    "primary_evidence_path",
    "status",
    "notes",
)
EVIDENCE_HEADER = (
    "source",
    "capture_uid",
    "capture_label",
    "capture_root_ref",
    "location_id",
    "location_kind",
    "location_label",
    "parent_location_id",
    "location_path",
    "identifier_kind",
    "normalized_identifier",
    "display_identifier",
    "network_scope",
    "controller",
    "parent_location_label",
    "evidence_kind",
    *EVIDENCE_PROVENANCE_HEADER,
    "confidence",
    "note",
)
ISSUE_HEADER = (
    "source",
    "capture_uid",
    "location_id",
    "issue_kind",
    "message",
    "evidence_path",
)


class RebuildLocationInventoryUseCase:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: LocationInventoryRequest) -> LocationInventoryResponse:
        normalized_root = path_from_ref(request.normalized_dataset_ref)
        output_path = path_from_ref(request.inventory_output_ref)
        ensure_output_not_within_input_tree(
            normalized_root,
            output_path,
            input_label="normalized root",
            output_label="location inventory aggregate output",
        )
        evidence_rows = self._collect_evidence_rows(normalized_root, output_path)
        inventory_rows, issue_rows = summarize_location_inventory(evidence_rows)

        self._artifacts.write_rows(output_path, INVENTORY_HEADER, inventory_rows)
        self._artifacts.write_rows(
            output_path.with_name("location_inventory_evidence.csv"),
            EVIDENCE_HEADER,
            evidence_rows,
        )
        self._artifacts.write_rows(
            output_path.with_name("location_inventory_issues.csv"),
            ISSUE_HEADER,
            issue_rows,
        )
        self._artifacts.write_json(
            output_path.with_name("location_inventory_summary.json"),
            {
                "location_count": len(inventory_rows),
                "evidence_count": len(evidence_rows),
                "issue_count": len(issue_rows),
            },
        )
        return LocationInventoryResponse(
            inventory_output_ref=request.inventory_output_ref,
            location_count=len(inventory_rows),
            evidence_count=len(evidence_rows),
            issue_count=len(issue_rows),
        )

    def _collect_evidence_rows(
        self, normalized_root: Path, output_path: Path
    ) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        seen: set[tuple[str, ...]] = set()
        for path in iter_tree_files(normalized_root, exclude_paths=(output_path,)):
            if path.name != "location_inventory.csv":
                continue
            for row in self._artifacts.read_rows(path):
                normalized_identifier = row.get("normalized_identifier") or row.get(
                    "identifier_value", ""
                )
                evidence_row = {
                    "source": row.get("source", ""),
                    "capture_uid": row.get("capture_uid", ""),
                    "capture_label": row.get("capture_label", ""),
                    "capture_root_ref": row.get("capture_root_ref", ""),
                    "location_id": row.get("location_id", ""),
                    "location_kind": row.get("location_kind", ""),
                    "location_label": row.get("location_label", ""),
                    "parent_location_id": row.get("parent_location_id", ""),
                    "location_path": row.get("location_path", ""),
                    "identifier_kind": row.get("identifier_kind", ""),
                    "normalized_identifier": normalized_identifier,
                    "display_identifier": row.get("display_identifier", "")
                    or normalized_identifier,
                    "network_scope": row.get("network_scope", ""),
                    "controller": row.get("controller", ""),
                    "parent_location_label": row.get("parent_location_label", ""),
                    "evidence_kind": row.get("evidence_kind", ""),
                    **_evidence_provenance_columns(row),
                    "confidence": row.get("confidence", ""),
                    "note": row.get("notes", ""),
                }
                key = tuple(evidence_row[column] for column in EVIDENCE_HEADER)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(evidence_row)
        return rows


def _evidence_provenance_columns(row: dict[str, str]) -> dict[str, str]:
    return {column: row.get(column, "") for column in EVIDENCE_PROVENANCE_HEADER}
