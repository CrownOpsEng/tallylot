from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.dtos import (
    ManifestRequest,
    ScreenBatchRequest,
    StageBatchRequest,
    VerificationCompareRequest,
    WalletInventoryRequest,
)
from crypto_reconciliation.application.services.manifest import ManifestService
from crypto_reconciliation.application.services.staging import BatchScreeningService, BatchStagingService
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


def test_manifest_service_excludes_manifest_output_from_source_scan(
    structured_source_dir: Path,
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    (source_dir / "transactions.csv").write_text(
        (structured_source_dir / "transactions.csv").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    output_path = source_dir / "manifest.csv"
    service = ManifestService(FilesystemArtifactStore())

    first = service.execute(ManifestRequest(source_dir=source_dir, output_path=output_path))
    second = service.execute(ManifestRequest(source_dir=source_dir, output_path=output_path))

    assert first.file_count == 1
    assert second.file_count == 1
    assert first.manifest_fingerprint == second.manifest_fingerprint


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
    artifacts = FilesystemArtifactStore()

    response = BatchStagingService(BatchScreeningService(artifacts)).execute(
        StageBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=tmp_path / "batch",
        ),
    )

    assert response.staged is False
    assert response.duplicate_count == 1


def test_batch_screening_surfaces_missing_required_candidate_fields(
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
                "Comment": "missing-date",
                "Date": "",
                "Tx-ID": "tx-2",
            },
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
                "Comment": "missing-txid",
                "Date": "2023-08-06 10:00:00",
                "Tx-ID": "",
            },
        ),
    )
    output_dir = tmp_path / "screen"
    artifacts = FilesystemArtifactStore()

    response = BatchScreeningService(artifacts).execute(
        ScreenBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=output_dir,
        )
    )

    issue_rows = artifacts.read_rows(output_dir / "stage_issues.csv")

    assert response.passed is False
    assert response.issue_count == 2
    assert [row["kind"] for row in issue_rows] == ["missing_date", "missing_tx_id"]


def test_batch_screening_surfaces_invalid_candidate_timestamps(
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
                "Comment": "invalid-date",
                "Date": "2023/08/06 10:00:00",
                "Tx-ID": "tx-2",
            },
        ),
    )
    output_dir = tmp_path / "screen"
    artifacts = FilesystemArtifactStore()

    response = BatchScreeningService(artifacts).execute(
        ScreenBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=output_dir,
        )
    )

    issue_rows = artifacts.read_rows(output_dir / "stage_issues.csv")

    assert response.passed is False
    assert response.issue_count == 1
    assert issue_rows[0]["kind"] == "invalid_date"


def test_wallet_inventory_service_deduplicates_rows(tmp_path: Path) -> None:
    normalized_root = tmp_path / "normalized"
    normalized_a = normalized_root / "a" / "wallet_inventory.csv"
    normalized_b = normalized_root / "b" / "wallet_inventory.csv"
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
        "evidence_path": "transactions.csv",
        "identifier_kind": "account_wallet",
        "identifier_value": "Account:Wallet",
        "notes": "",
    }
    write_rows(normalized_a, header, (row,))
    write_rows(normalized_b, header, (row,))

    response = WalletInventoryService(FilesystemArtifactStore()).execute(
        WalletInventoryRequest(normalized_root=normalized_root, output_path=tmp_path / "wallets.csv"),
    )

    assert response.wallet_count == 1
    assert response.evidence_count == 1
    assert response.issue_count == 0


def test_wallet_inventory_service_excludes_stale_aggregate_output(tmp_path: Path) -> None:
    normalized_root = tmp_path / "normalized"
    wallet_file = normalized_root / "source" / "wallet_inventory.csv"
    output_path = tmp_path / "wallet_inventory.csv"
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
        "evidence_path": "transactions.csv",
        "identifier_kind": "account_wallet",
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
