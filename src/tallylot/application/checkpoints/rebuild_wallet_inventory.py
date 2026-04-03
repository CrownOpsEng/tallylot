"""Rebuild checkpoint-supporting wallet inventory aggregates."""

from __future__ import annotations

from tallylot.application.checkpoints.contracts import WalletInventoryRequest, WalletInventoryResponse
from tallylot.application.checkpoints.wallet_inventory_summary import summarize_wallet_inventory
from tallylot.application.workspace.filesystem import ensure_output_not_within_input_tree, iter_tree_files
from tallylot.ports.artifacts import ArtifactStorePort

INVENTORY_HEADER = (
    "wallet_id",
    "identifier_kind",
    "normalized_identifier",
    "display_identifier",
    "network_scopes",
    "source_labels",
    "controller_labels",
    "account_labels",
    "evidence_count",
    "primary_evidence_path",
    "status",
    "notes",
)
EVIDENCE_HEADER = (
    "source",
    "capture_path",
    "wallet_id",
    "identifier_kind",
    "normalized_identifier",
    "display_identifier",
    "network_scope",
    "controller",
    "account_label",
    "evidence_kind",
    "evidence_path",
    "confidence",
    "note",
)
ISSUE_HEADER = (
    "source",
    "capture_path",
    "wallet_id",
    "issue_kind",
    "message",
    "evidence_path",
)


class RebuildWalletInventoryUseCase:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: WalletInventoryRequest) -> WalletInventoryResponse:
        ensure_output_not_within_input_tree(
            request.normalized_root,
            request.output_path,
            input_label="normalized root",
            output_label="wallet inventory aggregate output",
        )
        evidence_rows = self._collect_evidence_rows(request)
        inventory_rows, issue_rows = summarize_wallet_inventory(evidence_rows)

        self._artifacts.write_rows(request.output_path, INVENTORY_HEADER, inventory_rows)
        self._artifacts.write_rows(
            request.output_path.with_name("wallet_inventory_evidence.csv"),
            EVIDENCE_HEADER,
            evidence_rows,
        )
        self._artifacts.write_rows(
            request.output_path.with_name("wallet_inventory_issues.csv"),
            ISSUE_HEADER,
            issue_rows,
        )
        self._artifacts.write_json(
            request.output_path.with_name("wallet_inventory_summary.json"),
            {
                "wallet_count": len(inventory_rows),
                "evidence_count": len(evidence_rows),
                "issue_count": len(issue_rows),
            },
        )
        return WalletInventoryResponse(
            output_path=request.output_path,
            wallet_count=len(inventory_rows),
            evidence_count=len(evidence_rows),
            issue_count=len(issue_rows),
        )

    def _collect_evidence_rows(self, request: WalletInventoryRequest) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        seen: set[tuple[str, ...]] = set()
        for path in iter_tree_files(request.normalized_root, exclude_paths=(request.output_path,)):
            if path.name != "wallet_inventory.csv":
                continue
            for row in self._artifacts.read_rows(path):
                normalized_identifier = row.get("normalized_identifier") or row.get("identifier_value", "")
                evidence_row = {
                    "source": row.get("source", ""),
                    "capture_path": row.get("capture_path", ""),
                    "wallet_id": row.get("wallet_id", ""),
                    "identifier_kind": row.get("identifier_kind", ""),
                    "normalized_identifier": normalized_identifier,
                    "display_identifier": row.get("display_identifier", "") or normalized_identifier,
                    "network_scope": row.get("network_scope", ""),
                    "controller": row.get("controller", ""),
                    "account_label": row.get("account_label", "") or row.get("wallet", ""),
                    "evidence_kind": row.get("evidence_kind", ""),
                    "evidence_path": row.get("evidence_path", ""),
                    "confidence": row.get("confidence", ""),
                    "note": row.get("notes", ""),
                }
                key = tuple(evidence_row[column] for column in EVIDENCE_HEADER)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(evidence_row)
        return rows
