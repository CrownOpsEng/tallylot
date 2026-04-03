from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.dtos import (
    ManifestRequest,
    StageBatchRequest,
    VerificationCompareRequest,
    WalletInventoryRequest,
)
from crypto_reconciliation.application.services.manifest import ManifestService
from crypto_reconciliation.application.services.staging import BatchStagingService
from crypto_reconciliation.application.services.verification import VerificationCompareService
from crypto_reconciliation.application.services.wallet_inventory import WalletInventoryService
from crypto_reconciliation.infrastructure.serialization.csv_io import write_rows
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_manifest_service_writes_manifest(structured_source_dir: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "manifest.csv"

    response = ManifestService(FilesystemArtifactStore()).execute(
        ManifestRequest(source_dir=structured_source_dir, output_path=output_path),
    )

    assert response.file_count == 1
    assert response.manifest_fingerprint
    assert output_path.exists()


def test_verification_compare_service_writes_summary(
    verification_previous_dir: Path,
    verification_current_dir: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "verification"

    response = VerificationCompareService(FilesystemArtifactStore()).execute(
        VerificationCompareRequest(
            previous_dir=verification_previous_dir,
            current_dir=verification_current_dir,
            output_dir=output_dir,
        ),
    )

    assert response.changed_reports == 1
    assert (output_dir / "verification_summary.json").exists()


def test_batch_staging_detects_duplicates(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "candidate.csv"
    write_rows(
        candidate_path,
        (
            "Type",
            "Buy",
            "Cur.",
            "Sell",
            "Cur..1",
            "Fee",
            "Cur..2",
            "Exchange",
            "Group",
            "Comment",
            "Date",
            "Tx-ID",
        ),
        (
            {
                "Type": "Trade",
                "Buy": "1.0",
                "Cur.": "BTC",
                "Sell": "10.0",
                "Cur..1": "CAD",
                "Fee": "0.1",
                "Cur..2": "CAD",
                "Exchange": "Fixture",
                "Group": "",
                "Comment": "dup",
                "Date": "2023-08-06 10:00:00",
                "Tx-ID": "tx-1",
            },
        ),
    )

    response = BatchStagingService(FilesystemArtifactStore()).execute(
        StageBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=tmp_path / "batch",
        ),
    )

    assert response.staged is False
    assert response.duplicate_count == 1


def test_wallet_inventory_service_deduplicates_rows(tmp_path: Path) -> None:
    normalized_a = tmp_path / "a" / "wallet_inventory.csv"
    normalized_b = tmp_path / "b" / "wallet_inventory.csv"
    header = (
        "wallet_id",
        "source",
        "account",
        "wallet",
        "evidence_path",
        "identifier_kind",
        "identifier_value",
        "notes",
    )
    row = {
        "wallet_id": "wallet-1",
        "source": "fixture",
        "account": "Account",
        "wallet": "Wallet",
        "evidence_path": "/tmp/evidence.csv",
        "identifier_kind": "account_wallet",
        "identifier_value": "Account:Wallet",
        "notes": "",
    }
    write_rows(normalized_a, header, (row,))
    write_rows(normalized_b, header, (row,))

    response = WalletInventoryService(FilesystemArtifactStore()).execute(
        WalletInventoryRequest(normalized_root=tmp_path, output_path=tmp_path / "wallets.csv"),
    )

    assert response.wallet_count == 1
