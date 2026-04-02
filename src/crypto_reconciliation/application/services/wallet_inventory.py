"""Wallet inventory aggregation service."""

from __future__ import annotations

from crypto_reconciliation.application.dtos import WalletInventoryRequest, WalletInventoryResponse
from crypto_reconciliation.application.services.scan import (
    ensure_output_not_within_input_tree,
    iter_tree_files,
)
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

EVIDENCE_HEADER = (
    "wallet_id",
    "source",
    "account",
    "wallet",
    "identifier_kind",
    "identifier_value",
    "evidence_path",
)
ISSUE_HEADER = (
    "wallet_id",
    "source",
    "identifier_kind",
    "identifier_value",
    "issue_kind",
    "message",
)


class WalletInventoryService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: WalletInventoryRequest) -> WalletInventoryResponse:
        ensure_output_not_within_input_tree(
            request.normalized_root,
            request.output_path,
            input_label="normalized root",
            output_label="wallet inventory aggregate output",
        )
        rows: list[dict[str, str]] = []
        evidence_rows: list[dict[str, str]] = []
        issue_rows: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        wallets_by_identifier: dict[tuple[str, str], set[str]] = {}
        for path in iter_tree_files(request.normalized_root, exclude_paths=(request.output_path,)):
            if path.name != "wallet_inventory.csv":
                continue
            for row in self._artifacts.read_rows(path):
                key = (row["wallet_id"], row["identifier_kind"], row["identifier_value"])
                wallets_by_identifier.setdefault(
                    (row["identifier_kind"], row["identifier_value"]),
                    set(),
                ).add(row["wallet_id"])
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)
                evidence_rows.append(
                    {
                        "wallet_id": row["wallet_id"],
                        "source": row["source"],
                        "account": row["account"],
                        "wallet": row["wallet"],
                        "identifier_kind": row["identifier_kind"],
                        "identifier_value": row["identifier_value"],
                        "evidence_path": row["evidence_path"],
                    }
                )
                if not row["evidence_path"]:
                    issue_rows.append(
                        {
                            "wallet_id": row["wallet_id"],
                            "source": row["source"],
                            "identifier_kind": row["identifier_kind"],
                            "identifier_value": row["identifier_value"],
                            "issue_kind": "missing_evidence_path",
                            "message": "Wallet inventory rows must retain a source-relative evidence path.",
                        }
                    )
        for (identifier_kind, identifier_value), wallet_ids in sorted(wallets_by_identifier.items()):
            if len(wallet_ids) > 1:
                wallet_id = sorted(wallet_ids)[0]
                issue_rows.append(
                    {
                        "wallet_id": wallet_id,
                        "source": "",
                        "identifier_kind": identifier_kind,
                        "identifier_value": identifier_value,
                        "issue_kind": "conflicting_wallet_id",
                        "message": (
                            "The same identifier value maps to more than one wallet_id across normalized inputs."
                        ),
                    }
                )
        self._artifacts.write_rows(
            request.output_path,
            (
                "wallet_id",
                "source",
                "account",
                "wallet",
                "evidence_path",
                "identifier_kind",
                "identifier_value",
                "notes",
            ),
            rows,
        )
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
                "wallet_count": len(rows),
                "evidence_count": len(evidence_rows),
                "issue_count": len(issue_rows),
            },
        )
        return WalletInventoryResponse(
            output_path=request.output_path,
            wallet_count=len(rows),
            evidence_count=len(evidence_rows),
            issue_count=len(issue_rows),
        )
