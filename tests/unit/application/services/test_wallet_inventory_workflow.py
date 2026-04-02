from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.models.wallet import WalletInventoryRequest
from crypto_reconciliation.application.services.wallet_inventory import WalletInventoryService
from crypto_reconciliation.infrastructure.serialization.csv_io import write_rows
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore


def _wallet_inventory_header() -> tuple[str, ...]:
    return (
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
        "account",
        "wallet",
        "identifier_value",
        "notes",
    )


def test_wallet_inventory_service_deduplicates_rows(tmp_path: Path) -> None:
    normalized_root = tmp_path / "normalized"
    normalized_a = normalized_root / "a" / "wallet_inventory.csv"
    normalized_b = normalized_root / "b" / "wallet_inventory.csv"
    header = _wallet_inventory_header()
    row = {
        "source": "fixture",
        "capture_path": "raw/transactions.csv",
        "wallet_id": "wallet-1",
        "identifier_kind": "account_wallet",
        "normalized_identifier": "Account:Wallet",
        "display_identifier": "Account:Wallet",
        "network_scope": "accounting",
        "controller": "Fixture Controller",
        "account_label": "Account",
        "evidence_kind": "normalized_transactions",
        "evidence_path": "normalized/transactions.csv",
        "confidence": "high",
        "account": "Account",
        "wallet": "Wallet",
        "identifier_value": "Account:Wallet",
        "notes": "primary",
    }
    write_rows(normalized_a, header, (row,))
    write_rows(normalized_b, header, (row,))

    response = WalletInventoryService(FilesystemArtifactStore()).execute(
        WalletInventoryRequest(normalized_root=normalized_root, output_path=tmp_path / "wallets.csv"),
    )

    inventory_rows = FilesystemArtifactStore().read_rows(tmp_path / "wallets.csv")
    evidence_rows = FilesystemArtifactStore().read_rows(tmp_path / "wallet_inventory_evidence.csv")

    assert response.wallet_count == 1
    assert response.evidence_count == 1
    assert response.issue_count == 0
    assert inventory_rows[0]["controller_labels"] == "Fixture Controller"
    assert inventory_rows[0]["status"] == "ready"
    assert evidence_rows[0]["note"] == "primary"


def test_wallet_inventory_service_marks_aliases_and_flags_identifier_conflicts(tmp_path: Path) -> None:
    normalized_root = tmp_path / "normalized"
    alias_file = normalized_root / "alias" / "wallet_inventory.csv"
    address_file = normalized_root / "address" / "wallet_inventory.csv"
    header = _wallet_inventory_header()
    write_rows(
        alias_file,
        header,
        (
            {
                "source": "gtrade",
                "capture_path": "raw/gtrade.csv",
                "wallet_id": "wallet-alias",
                "identifier_kind": "address_alias",
                "normalized_identifier": "0xabc123",
                "display_identifier": "0xabc...123",
                "network_scope": "arbitrum",
                "controller": "EVM Wallet",
                "account_label": "Trading",
                "evidence_kind": "statement_alias",
                "evidence_path": "normalized/gtrade.csv",
                "confidence": "medium",
                "account": "Trading",
                "wallet": "EVM Wallet",
                "identifier_value": "0xabc123",
                "notes": "truncated alias only",
            },
        ),
    )
    write_rows(
        address_file,
        header,
        (
            {
                "source": "evm_explorer",
                "capture_path": "raw/explorer.csv",
                "wallet_id": "wallet-address",
                "identifier_kind": "address",
                "normalized_identifier": "0xabc123",
                "display_identifier": "0xabc123",
                "network_scope": "arbitrum",
                "controller": "EVM Wallet",
                "account_label": "Trading",
                "evidence_kind": "explorer_address",
                "evidence_path": "normalized/explorer.csv",
                "confidence": "high",
                "account": "Trading",
                "wallet": "EVM Wallet",
                "identifier_value": "0xabc123",
                "notes": "",
            },
        ),
    )

    response = WalletInventoryService(FilesystemArtifactStore()).execute(
        WalletInventoryRequest(normalized_root=normalized_root, output_path=tmp_path / "wallets.csv"),
    )

    inventory_rows = FilesystemArtifactStore().read_rows(tmp_path / "wallets.csv")
    issue_rows = FilesystemArtifactStore().read_rows(tmp_path / "wallet_inventory_issues.csv")
    inventory_by_wallet = {row["wallet_id"]: row for row in inventory_rows}

    assert response.wallet_count == 2
    assert response.issue_count == 1
    assert inventory_by_wallet["wallet-alias"]["status"] == "needs_linked_evidence"
    assert issue_rows[0]["issue_kind"] == "identifier_kind_conflict"
    assert issue_rows[0]["evidence_path"] == "0xabc123"


def test_wallet_inventory_service_excludes_stale_aggregate_output(tmp_path: Path) -> None:
    normalized_root = tmp_path / "normalized"
    wallet_file = normalized_root / "source" / "wallet_inventory.csv"
    output_path = tmp_path / "wallet_inventory.csv"
    header = _wallet_inventory_header()
    row = {
        "source": "fixture",
        "capture_path": "raw/transactions.csv",
        "wallet_id": "wallet-1",
        "identifier_kind": "account_wallet",
        "normalized_identifier": "Account:Wallet",
        "display_identifier": "Account:Wallet",
        "network_scope": "",
        "controller": "",
        "account_label": "Account",
        "evidence_kind": "normalized_transactions",
        "evidence_path": "transactions.csv",
        "confidence": "high",
        "account": "Account",
        "wallet": "Wallet",
        "identifier_value": "Account:Wallet",
        "notes": "",
    }
    write_rows(wallet_file, header, (row,))
    service = WalletInventoryService(FilesystemArtifactStore())

    first = service.execute(WalletInventoryRequest(normalized_root=normalized_root, output_path=output_path))
    wallet_file.unlink()
    second = service.execute(WalletInventoryRequest(normalized_root=normalized_root, output_path=output_path))

    assert first.wallet_count == 1
    assert second.wallet_count == 0
