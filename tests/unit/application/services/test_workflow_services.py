from __future__ import annotations

import json
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
from tests.support.verification import VerificationFixtureSet, write_verification_set


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


def test_verification_compare_service_detects_new_issues_and_balance_changes(tmp_path: Path) -> None:
    previous_dir = tmp_path / "previous"
    current_dir = tmp_path / "current"
    output_dir = tmp_path / "verification"
    previous_dir.mkdir()
    current_dir.mkdir()
    write_verification_set(
        previous_dir,
        VerificationFixtureSet(
            validate_rows=({"Issue": "AXS"},),
            missing_rows=(
                {
                    "Type": "Deposit",
                    "Amount": "1.0",
                    "Cur.": "BTC",
                    "Fee": "",
                    "Fee Cur.": "",
                    "Value in CAD": "1.0",
                    "Exchange": "Coinbase",
                    "Trade Group": "",
                    "Comment": "",
                    "Trade ID": "trade-1",
                    "Date": "2023-08-05 08:34:04",
                    "Match": "",
                    "": "",
                },
            ),
            duplicate_rows=(),
            current_balance_rows=(
                {"Ticker": "BTC", "Name": "Bitcoin", "Type": "Coin", "Amount": "1.00000000", "Value in CAD": "10.0"},
                {
                    "Ticker": "CAD",
                    "Name": "Canadian Dollar",
                    "Type": "Currency",
                    "Amount": "0.00000000",
                    "Value in CAD": "0",
                },
            ),
            exchange_rows=(
                {
                    "Amount": "1.00000000",
                    "Currency": "BTC",
                    "Current value in CAD": "10.0",
                    "Current value in BTC": "0.1",
                    "Exchange": "Coinbase",
                },
            ),
        ),
    )
    write_verification_set(
        current_dir,
        VerificationFixtureSet(
            validate_rows=({"Issue": "AXS"}, {"Issue": "NEW"}),
            missing_rows=(
                {
                    "Type": "Deposit",
                    "Amount": "1.0",
                    "Cur.": "BTC",
                    "Fee": "",
                    "Fee Cur.": "",
                    "Value in CAD": "1.0",
                    "Exchange": "Coinbase",
                    "Trade Group": "",
                    "Comment": "",
                    "Trade ID": "trade-1",
                    "Date": "2023-08-05 08:34:04",
                    "Match": "",
                    "": "",
                },
            ),
            duplicate_rows=(
                {
                    "": "",
                    "# of duplicates": "2",
                    "Type": "Trade",
                    "Exchange": "Coinbase",
                    "Exchange ID": "id-1",
                    "Buy": "1 BTC",
                    "Sell": "10 CAD",
                    "Trade Group": "",
                    "Tx ID": "tx-1",
                    "Tx Date": "2023-08-05 08:35:00",
                },
            ),
            current_balance_rows=(
                {"Ticker": "BTC", "Name": "Bitcoin", "Type": "Coin", "Amount": "2.50000000", "Value in CAD": "25.0"},
                {
                    "Ticker": "CAD",
                    "Name": "Canadian Dollar",
                    "Type": "Currency",
                    "Amount": "-5.00000000",
                    "Value in CAD": "-5",
                },
            ),
            exchange_rows=(
                {
                    "Amount": "2.50000000",
                    "Currency": "BTC",
                    "Current value in CAD": "25.0",
                    "Current value in BTC": "0.2",
                    "Exchange": "Coinbase",
                },
                {
                    "Amount": "-5.00000000",
                    "Currency": "CAD",
                    "Current value in CAD": "-5.0",
                    "Current value in BTC": "-0.05",
                    "Exchange": "Bank",
                },
            ),
        ),
    )

    response = VerificationCompareService(FilesystemArtifactStore()).execute(
        VerificationCompareRequest(
            previous_dir=previous_dir,
            current_dir=current_dir,
            output_dir=output_dir,
        ),
    )

    summary = json.loads((output_dir / "verification_summary.json").read_text(encoding="utf-8"))
    duplicate_rows = FilesystemArtifactStore().read_rows(output_dir / "current_duplicate_transaction_rows.csv")
    delta_rows = FilesystemArtifactStore().read_rows(output_dir / "current_balance_deltas.csv")

    assert response.changed_reports == 4
    assert response.gate_suggestion == "hold"
    assert summary["new_validate_rows"] == 1
    assert summary["current_duplicate_rows"] == 1
    assert summary["current_negative_balance_rows"] == 1
    assert summary["gate_flags"]["has_duplicate_rows"] is True
    assert duplicate_rows[0]["Tx ID"] == "tx-1"
    assert {row["ticker"] for row in delta_rows} == {"BTC", "CAD"}


def test_verification_compare_service_detects_resolved_rows_without_new_issues(tmp_path: Path) -> None:
    previous_dir = tmp_path / "previous"
    current_dir = tmp_path / "current"
    output_dir = tmp_path / "verification"
    previous_dir.mkdir()
    current_dir.mkdir()
    write_verification_set(
        previous_dir,
        VerificationFixtureSet(
            validate_rows=({"Issue": "AXS"},),
            missing_rows=(
                {
                    "Type": "Deposit",
                    "Amount": "1.0",
                    "Cur.": "BTC",
                    "Fee": "",
                    "Fee Cur.": "",
                    "Value in CAD": "1.0",
                    "Exchange": "Coinbase",
                    "Trade Group": "",
                    "Comment": "",
                    "Trade ID": "trade-1",
                    "Date": "2023-08-05 08:34:04",
                    "Match": "",
                    "": "",
                },
            ),
            duplicate_rows=(),
            current_balance_rows=(
                {"Ticker": "BTC", "Name": "Bitcoin", "Type": "Coin", "Amount": "1.00000000", "Value in CAD": "10.0"},
            ),
            exchange_rows=(
                {
                    "Amount": "1.00000000",
                    "Currency": "BTC",
                    "Current value in CAD": "10.0",
                    "Current value in BTC": "0.1",
                    "Exchange": "Coinbase",
                },
            ),
        ),
    )
    write_verification_set(
        current_dir,
        VerificationFixtureSet(
            validate_rows=(),
            missing_rows=(),
            duplicate_rows=(),
            current_balance_rows=(
                {"Ticker": "BTC", "Name": "Bitcoin", "Type": "Coin", "Amount": "1.00000000", "Value in CAD": "10.0"},
            ),
            exchange_rows=(
                {
                    "Amount": "1.00000000",
                    "Currency": "BTC",
                    "Current value in CAD": "10.0",
                    "Current value in BTC": "0.1",
                    "Exchange": "Coinbase",
                },
            ),
        ),
    )

    response = VerificationCompareService(FilesystemArtifactStore()).execute(
        VerificationCompareRequest(
            previous_dir=previous_dir,
            current_dir=current_dir,
            output_dir=output_dir,
        ),
    )

    summary = json.loads((output_dir / "verification_summary.json").read_text(encoding="utf-8"))
    resolved_missing_rows = FilesystemArtifactStore().read_rows(output_dir / "resolved_missing_transaction_rows.csv")

    assert response.changed_reports == 2
    assert response.gate_suggestion == "review_balance_changes"
    assert summary["resolved_validate_rows"] == 1
    assert summary["resolved_missing_rows"] == 1
    assert resolved_missing_rows[0]["Trade ID"] == "trade-1"


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


def test_batch_screening_writes_overlap_artifacts_for_review_required_candidates(
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
                "Comment": "overlap",
                "Date": "2023-08-05 08:34:04",
                "Tx-ID": "tx-1",
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

    overlap_summary = json.loads((output_dir / "overlap_check" / "overlap_summary.json").read_text(encoding="utf-8"))
    overlap_rows = artifacts.read_rows(output_dir / "overlap_check" / "overlap_flagged_rows.csv")

    assert response.passed is False
    assert response.overlap_rows_flagged == 1
    assert overlap_summary["status"] == "review_required"
    assert overlap_rows[0]["reasons"] == "on_or_before_cutoff;baseline_tx_id_match;baseline_economic_signature_match"


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


def test_batch_staging_uses_normalization_summary_window_and_import_ready_copy(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    normalized_dir = tmp_path / "normalized"
    normalized_dir.mkdir()
    candidate_path = normalized_dir / "candidate.csv"
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
                "Comment": "window-ok",
                "Date": "2024-01-01 00:00:00",
                "Tx-ID": "tx-2",
            },
        ),
    )
    (normalized_dir / "normalization_summary.json").write_text(
        json.dumps(
            {
                "normalization_window_start": "2023-08-05 08:34:05",
                "normalization_window_end": "2024-12-31 23:59:59",
            }
        ),
        encoding="utf-8",
    )

    response = BatchStagingService(BatchScreeningService(FilesystemArtifactStore())).execute(
        StageBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=tmp_path / "batch",
            import_ready_dir=tmp_path / "ready",
            staged_name="approved.csv",
        ),
    )

    summary = json.loads((tmp_path / "batch" / "stage_summary.json").read_text(encoding="utf-8"))

    assert response.staged is True
    assert response.staged_path == tmp_path / "batch" / "approved.csv"
    assert response.import_ready_copy_path == tmp_path / "ready" / "approved.csv"
    assert summary["normalization_summary"].endswith("normalization_summary.json")
    assert summary["rows_outside_normalization_window"] == 0


def test_batch_staging_explicit_window_overrides_normalization_summary(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    normalized_dir = tmp_path / "normalized"
    normalized_dir.mkdir()
    candidate_path = normalized_dir / "candidate.csv"
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
                "Comment": "window-override",
                "Date": "2024-01-01 00:00:00",
                "Tx-ID": "tx-2",
            },
        ),
    )
    (normalized_dir / "normalization_summary.json").write_text(
        json.dumps(
            {
                "normalization_window_start": "2023-08-05 08:34:05",
                "normalization_window_end": "2023-12-31 23:59:59",
            }
        ),
        encoding="utf-8",
    )

    response = BatchStagingService(BatchScreeningService(FilesystemArtifactStore())).execute(
        StageBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=tmp_path / "batch",
            normalization_summary_path=normalized_dir / "normalization_summary.json",
            window_end="2024-12-31 23:59:59",
        ),
    )

    summary = json.loads((tmp_path / "batch" / "stage_summary.json").read_text(encoding="utf-8"))

    assert response.staged is True
    assert summary["normalization_window_end"] == "2024-12-31 23:59:59"
    assert summary["rows_outside_normalization_window"] == 0


def test_batch_staging_blocks_candidates_outside_normalization_window(
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
                "Comment": "too-late",
                "Date": "2026-01-01 00:00:00",
                "Tx-ID": "tx-2",
            },
        ),
    )

    response = BatchStagingService(BatchScreeningService(FilesystemArtifactStore())).execute(
        StageBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=tmp_path / "batch",
        ),
    )

    summary = json.loads((tmp_path / "batch" / "stage_summary.json").read_text(encoding="utf-8"))

    assert response.staged is False
    assert "normalization_window_mismatch" in response.blocked_reason_codes
    assert summary["rows_outside_normalization_window"] == 1


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
