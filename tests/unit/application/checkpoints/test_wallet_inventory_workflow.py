from __future__ import annotations

from pathlib import Path

from tallylot.application.checkpoints import (
    LocationInventoryRequest,
    RebuildLocationInventoryUseCase,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.serialization.csv_io import write_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


def _location_inventory_header() -> tuple[str, ...]:
    return (
        "source",
        "capture_uid",
        "capture_label",
        "capture_root_ref",
        "location_id",
        "identifier_kind",
        "normalized_identifier",
        "display_identifier",
        "network_scope",
        "controller",
        "location_kind",
        "location_label",
        "parent_location_id",
        "location_path",
        "parent_location_label",
        "evidence_kind",
        "evidence_path",
        "confidence",
        "identifier_value",
        "notes",
    )


def test_location_inventory_service_deduplicates_rows(tmp_path: Path) -> None:
    normalized_root = tmp_path / "normalized"
    normalized_a = normalized_root / "a" / "location_inventory.csv"
    normalized_b = normalized_root / "b" / "location_inventory.csv"
    header = _location_inventory_header()
    row = {
        "source": "fixture",
        "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
        "capture_label": "2026-03-23T14-15-16Z",
        "capture_root_ref": "evidence/raw/source/fixture/2026-03-23T14-15-16Z",
        "location_id": "location-1",
        "identifier_kind": "account_wallet",
        "normalized_identifier": "Account:Wallet",
        "display_identifier": "Account:Wallet",
        "network_scope": "accounting",
        "controller": "Fixture Controller",
        "location_kind": "account",
        "location_label": "Account",
        "parent_location_id": "",
        "location_path": "Account / Wallet",
        "parent_location_label": "",
        "evidence_kind": "normalized_transactions",
        "evidence_path": "normalized/transactions.csv",
        "confidence": "high",
        "identifier_value": "Account:Wallet",
        "notes": "primary",
    }
    write_rows(normalized_a, header, (row,))
    write_rows(normalized_b, header, (row,))

    response = RebuildLocationInventoryUseCase(FilesystemArtifactStore()).execute(
        LocationInventoryRequest(
            normalized_dataset_ref=to_resource_ref(normalized_root),
            inventory_output_ref=to_resource_ref(tmp_path / "wallets.csv"),
        ),
    )

    inventory_rows = FilesystemArtifactStore().read_rows(tmp_path / "wallets.csv")
    evidence_rows = FilesystemArtifactStore().read_rows(
        tmp_path / "location_inventory_evidence.csv"
    )

    assert response.location_count == 1
    assert response.evidence_count == 1
    assert response.issue_count == 0
    assert inventory_rows[0]["controller_labels"] == "Fixture Controller"
    assert inventory_rows[0]["status"] == "ready"
    assert evidence_rows[0]["note"] == "primary"


def test_location_inventory_service_marks_aliases_and_flags_identifier_conflicts(
    tmp_path: Path,
) -> None:
    normalized_root = tmp_path / "normalized"
    alias_file = normalized_root / "alias" / "location_inventory.csv"
    address_file = normalized_root / "address" / "location_inventory.csv"
    header = _location_inventory_header()
    write_rows(
        alias_file,
        header,
        (
            {
                "source": "gtrade",
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9F",
                "capture_label": "2026-03-23T14-15-16Z",
                "capture_root_ref": "evidence/raw/source/gtrade/2026-03-23T14-15-16Z",
                "location_id": "location-alias",
                "identifier_kind": "address_alias",
                "normalized_identifier": "0xabc123",
                "display_identifier": "0xabc...123",
                "network_scope": "arbitrum",
                "controller": "EVM Wallet",
                "location_kind": "account",
                "location_label": "Trading",
                "parent_location_id": "",
                "location_path": "Trading",
                "parent_location_label": "",
                "evidence_kind": "statement_alias",
                "evidence_path": "normalized/gtrade.csv",
                "confidence": "medium",
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
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9G",
                "capture_label": "2026-03-23T14-15-17Z",
                "capture_root_ref": "evidence/raw/source/evm_explorer/2026-03-23T14-15-17Z",
                "location_id": "location-address",
                "identifier_kind": "address",
                "normalized_identifier": "0xabc123",
                "display_identifier": "0xabc123",
                "network_scope": "arbitrum",
                "controller": "EVM Wallet",
                "location_kind": "account",
                "location_label": "Trading",
                "parent_location_id": "",
                "location_path": "Trading",
                "parent_location_label": "",
                "evidence_kind": "explorer_address",
                "evidence_path": "normalized/explorer.csv",
                "confidence": "high",
                "identifier_value": "0xabc123",
                "notes": "",
            },
        ),
    )

    response = RebuildLocationInventoryUseCase(FilesystemArtifactStore()).execute(
        LocationInventoryRequest(
            normalized_dataset_ref=to_resource_ref(normalized_root),
            inventory_output_ref=to_resource_ref(tmp_path / "wallets.csv"),
        ),
    )

    inventory_rows = FilesystemArtifactStore().read_rows(tmp_path / "wallets.csv")
    issue_rows = FilesystemArtifactStore().read_rows(
        tmp_path / "location_inventory_issues.csv"
    )
    inventory_by_location = {row["location_id"]: row for row in inventory_rows}

    assert response.location_count == 2
    assert response.issue_count == 1
    assert inventory_by_location["location-alias"]["status"] == "needs_linked_evidence"
    assert issue_rows[0]["issue_kind"] == "identifier_kind_conflict"
    assert issue_rows[0]["evidence_path"] == "0xabc123"


def test_location_inventory_service_excludes_stale_aggregate_output(
    tmp_path: Path,
) -> None:
    normalized_root = tmp_path / "normalized"
    wallet_file = normalized_root / "source" / "location_inventory.csv"
    output_path = tmp_path / "location_inventory.csv"
    header = _location_inventory_header()
    row = {
        "source": "fixture",
        "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
        "capture_label": "2026-03-23T14-15-16Z",
        "capture_root_ref": "evidence/raw/source/fixture/2026-03-23T14-15-16Z",
        "location_id": "location-1",
        "identifier_kind": "account_wallet",
        "normalized_identifier": "Account:Wallet",
        "display_identifier": "Account:Wallet",
        "network_scope": "",
        "controller": "",
        "location_kind": "account",
        "location_label": "Account",
        "parent_location_id": "",
        "location_path": "Account / Wallet",
        "parent_location_label": "",
        "evidence_kind": "normalized_transactions",
        "evidence_path": "transactions.csv",
        "confidence": "high",
        "identifier_value": "Account:Wallet",
        "notes": "",
    }
    write_rows(wallet_file, header, (row,))
    service = RebuildLocationInventoryUseCase(FilesystemArtifactStore())

    first = service.execute(
        LocationInventoryRequest(
            normalized_dataset_ref=to_resource_ref(normalized_root),
            inventory_output_ref=to_resource_ref(output_path),
        )
    )
    wallet_file.unlink()
    second = service.execute(
        LocationInventoryRequest(
            normalized_dataset_ref=to_resource_ref(normalized_root),
            inventory_output_ref=to_resource_ref(output_path),
        )
    )

    assert first.location_count == 1
    assert second.location_count == 0
