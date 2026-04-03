"""Wallet inventory aggregation service."""

from __future__ import annotations

from crypto_reconciliation.application.dtos import WalletInventoryRequest, WalletInventoryResponse
from crypto_reconciliation.ports.artifacts import ArtifactStorePort


class WalletInventoryService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: WalletInventoryRequest) -> WalletInventoryResponse:
        rows: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for path in sorted(request.normalized_root.rglob("wallet_inventory.csv")):
            for row in self._artifacts.read_rows(path):
                key = (row["wallet_id"], row["identifier_kind"], row["identifier_value"])
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)
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
        return WalletInventoryResponse(output_path=request.output_path, wallet_count=len(rows))
