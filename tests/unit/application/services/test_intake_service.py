from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from crypto_reconciliation.application.dtos import IntakeApplyRequest, IntakePlanRequest
from crypto_reconciliation.application.services.intake import SourceIntakeService
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_source_intake_service_plans_archive_members_without_copying_them(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    archive_path = incoming_dir / "bundle.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("inner.csv", "a,b\n1,2\n")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    response = SourceIntakeService(FilesystemArtifactStore()).plan(
        IntakePlanRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
        )
    )

    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")

    assert response.file_count == 2
    assert any(row["action"] == "copy" and row["path"].endswith("bundle.zip") for row in plan_rows)
    assert any(row["action"] == "extract_copy" and row["archive_member_path"] == "inner.csv" for row in plan_rows)


def test_source_intake_service_applies_loose_files_into_workspace(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    source_file = incoming_dir / "transactions.csv"
    source_file.write_text("a,b\n1,2\n", encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    response = SourceIntakeService(FilesystemArtifactStore()).apply(
        IntakeApplyRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
        )
    )

    summary = json.loads((report_dir / "intake_summary.json").read_text(encoding="utf-8"))
    target = workspace_root / "evidence" / "raw" / "source" / "unclassified" / "incoming" / "transactions.csv"

    assert response.copied_count == 1
    assert target.exists()
    assert summary["copied_count"] == 1


def test_source_intake_service_applies_archive_members_into_workspace(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    archive_path = incoming_dir / "bundle.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("inner.csv", "a,b\n1,2\n")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    response = SourceIntakeService(FilesystemArtifactStore()).apply(
        IntakeApplyRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
        )
    )

    archive_target = (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "unclassified"
        / "incoming"
        / "bundle"
        / "archive"
        / "bundle.zip"
    )
    member_target = (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "unclassified"
        / "incoming"
        / "bundle"
        / "contents"
        / "inner.csv"
    )

    assert response.copied_count == 2
    assert archive_target.exists()
    assert member_target.exists()


def test_source_intake_service_routes_source_artifacts_to_source_aware_supporting_paths(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    image_path = incoming_dir / "2021" / "Binance" / "From Binance" / "Trade Analysis - ADA-USDT - Binance.png"
    scratch_csv = incoming_dir / "2021" / "Binance" / "2021 Isolated" / "test.csv"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    scratch_csv.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"png")
    scratch_csv.write_text("a,b\n1,2\n", encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    SourceIntakeService(FilesystemArtifactStore()).plan(
        IntakePlanRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
        )
    )

    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    by_name = {Path(row["path"]).name: row for row in plan_rows if not row["archive_member_path"]}

    assert by_name["Trade Analysis - ADA-USDT - Binance.png"]["role"] == "working_derivative"
    assert by_name["Trade Analysis - ADA-USDT - Binance.png"]["source_folder"] == "binance"
    assert "/working/supporting_artifacts/binance/" in by_name["Trade Analysis - ADA-USDT - Binance.png"]["target_path"]
    assert by_name["test.csv"]["role"] == "working_derivative"
    assert "/working/supporting_artifacts/binance/" in by_name["test.csv"]["target_path"]


def test_source_intake_service_routes_cointracking_html_and_sidecar_to_portfolio_capture(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    html_path = incoming_dir / "tmp" / "CoinTracking · Tax Declaration Export.html"
    sidecar_path = incoming_dir / "tmp" / "CoinTracking · Tax Declaration Export_files" / "style.min.css"
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(
        """
        <html>
        <head><title>CoinTracking · Tax Declaration Export</title></head>
        <body>Created by: CoinTracking as of: 06.04.2022 01:11</body>
        </html>
        """,
        encoding="utf-8",
    )
    sidecar_path.write_text("body{}", encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    SourceIntakeService(FilesystemArtifactStore()).plan(
        IntakePlanRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
        )
    )

    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    by_name = {Path(row["path"]).name: row for row in plan_rows}

    assert by_name["CoinTracking · Tax Declaration Export.html"]["role"] == "portfolio_export"
    assert by_name["CoinTracking · Tax Declaration Export.html"]["capture_id"] == "2022-04"
    assert (
        "/evidence/raw/portfolio/cointracking/2022-04/"
        in by_name["CoinTracking · Tax Declaration Export.html"]["target_path"]
    )
    assert by_name["style.min.css"]["role"] == "portfolio_sidecar"
    assert by_name["style.min.css"]["capture_id"] == "2022-04"


def test_source_intake_service_skips_subset_duplicate_packages(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    borrow_payload = (
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    )
    interest_payload = "Pair,Coin,Amount,Time,Interest Type\nADA/USDT,USDT,0.1,2021-05-25 12:53:03,Hourly\n"
    (incoming_dir / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    bundle_dir = incoming_dir / "2021" / "Binance" / "From Binance"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    (bundle_dir / "interest.csv").write_text(interest_payload, encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    SourceIntakeService(FilesystemArtifactStore()).plan(
        IntakePlanRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
        )
    )

    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    summary = json.loads((report_dir / "intake_summary.json").read_text(encoding="utf-8"))
    loose_row = next(row for row in plan_rows if row["path"].endswith("/incoming/borrow.csv"))
    bundle_row = next(row for row in plan_rows if row["path"].endswith("/From Binance/borrow.csv"))

    assert loose_row["package_status"] == "duplicate_package_subset"
    assert loose_row["placement_status"] == "package_duplicate_skip"
    assert loose_row["action"] == "skip"
    assert bundle_row["package_status"] == "primary"
    assert summary["duplicate_packages"] == 1


def test_source_intake_service_flags_repo_manifest_overlap_for_review(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    existing_capture = workspace_root / "evidence" / "raw" / "source" / "coinbase" / "2021-05"
    existing_capture.mkdir(parents=True, exist_ok=True)
    existing_file = existing_capture / "retail-export.csv"
    payload = (
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
        "Bought 0.01 BTC for 610 CAD\n"
    )
    existing_file.write_text(payload, encoding="utf-8")
    FilesystemArtifactStore().write_rows(
        existing_capture / "manifest.csv",
        ("filename", "sha256", "size_bytes", "source_paths"),
        (
            {
                "filename": existing_file.name,
                "sha256": "placeholder",
                "size_bytes": str(existing_file.stat().st_size),
                "source_paths": str(existing_file),
            },
        ),
    )

    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    incoming_file = incoming_dir / "retail-export.csv"
    incoming_file.write_text(payload, encoding="utf-8")
    report_dir = tmp_path / "reports"

    SourceIntakeService(FilesystemArtifactStore()).plan(
        IntakePlanRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
        )
    )

    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    row = next(item for item in plan_rows if item["archive_member_path"] == "")

    assert row["review_required"] == "yes"
    assert "repo_manifest_overlap" in row["review_codes"]
    assert "coinbase/2021-05" in row["review_reason"]


def test_source_intake_service_flags_existing_capture_window_overlap_for_review(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    existing_capture = workspace_root / "evidence" / "raw" / "source" / "binance" / "2021-05" / "existing"
    existing_capture.mkdir(parents=True, exist_ok=True)
    existing_file = existing_capture / "borrow.csv"
    existing_file.write_text(
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n",
        encoding="utf-8",
    )

    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    incoming_file = incoming_dir / "borrow.csv"
    incoming_file.write_text(existing_file.read_text(encoding="utf-8"), encoding="utf-8")
    report_dir = tmp_path / "reports"

    SourceIntakeService(FilesystemArtifactStore()).plan(
        IntakePlanRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
        )
    )

    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    row = next(item for item in plan_rows if item["archive_member_path"] == "")

    assert row["review_required"] == "yes"
    assert "raw_capture_overlap" in row["review_codes"]
    assert "binance/2021-05" in row["review_reason"]


def test_source_intake_service_routes_wallet_export_to_existing_inventory_source(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    source_inventory_path = workspace_root / "analysis" / "issues" / "source_inventory.csv"
    source_inventory_path.parent.mkdir(parents=True, exist_ok=True)
    FilesystemArtifactStore().write_rows(
        source_inventory_path,
        (
            "source",
            "status",
            "capture_path",
            "adapter",
            "normalization_status",
        ),
        (
            {
                "source": "eth-gala1",
                "status": "capture_complete",
                "capture_path": "evidence/raw/source/eth-gala1/2026-03",
                "adapter": "evm_explorer",
                "normalization_status": "ready",
            },
        ),
    )
    wallet_evidence_path = workspace_root / "analysis" / "inventory" / "wallet_inventory_evidence.csv"
    wallet_evidence_path.parent.mkdir(parents=True, exist_ok=True)
    FilesystemArtifactStore().write_rows(
        wallet_evidence_path,
        (
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
        ),
        (
            {
                "source": "eth-gala1",
                "capture_path": "/tmp/capture",
                "wallet_id": "evm_address:0x2222222222222222222222222222222222222222",
                "identifier_kind": "evm_address",
                "normalized_identifier": "0x2222222222222222222222222222222222222222",
                "display_identifier": "0x2222222222222222222222222222222222222222",
                "network_scope": "ethereum",
                "controller": "Explorer export",
                "account_label": "Account 2",
                "evidence_kind": "filename",
                "evidence_path": "/tmp/evidence.csv",
                "confidence": "high",
                "note": "",
            },
        ),
    )

    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    export_path = incoming_dir / "Account1-bsc export-address-token.csv"
    export_path.write_text(
        "Transaction Hash,Blockno,UnixTimestamp,DateTime (UTC),TokenValue,TokenSymbol,From,To\n"
        "0xabc,1,1710000000,2024-03-09 09:41:37,1,GALA,0x0,0x2222222222222222222222222222222222222222\n",
        encoding="utf-8",
    )
    report_dir = tmp_path / "reports"

    SourceIntakeService(FilesystemArtifactStore()).plan(
        IntakePlanRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
        )
    )

    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    row = next(item for item in plan_rows if item["archive_member_path"] == "")

    assert row["source_folder"] == "eth-gala1"
    assert row["inventory_match_status"] == "inventory_source_match"
    assert row["review_required"] == "no"


def test_source_intake_service_merges_same_cycle_near_duplicate_packages_on_apply(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    older = incoming_dir / "2021" / "Binance" / "202203291730-export"
    newer = incoming_dir / "2021" / "Binance" / "202203291830-export"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    borrow_payload = (
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    )
    interest_payload = "Pair,Coin,Amount,Time,Interest Type\nADA/USDT,USDT,0.1,2021-05-25 12:53:03,Hourly\n"
    repay_payload = (
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 13:53:03,0.0345,Auto repayment,CONFIRM\n"
    )
    (older / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    (older / "interest.csv").write_text(interest_payload, encoding="utf-8")
    (newer / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    (newer / "repay.csv").write_text(repay_payload, encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    SourceIntakeService(FilesystemArtifactStore()).apply(
        IntakeApplyRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
        )
    )

    summary = json.loads((report_dir / "intake_summary.json").read_text(encoding="utf-8"))
    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    manifest_rows = FilesystemArtifactStore().read_rows(
        workspace_root / "evidence" / "raw" / "source" / "binance" / "2021-05" / "manifest.csv"
    )
    filenames = {row["filename"] for row in manifest_rows}
    superseded = next(row for row in plan_rows if row["relative_path"].endswith("202203291730-export/borrow.csv"))

    assert summary["merge_primary_packages"] == 1
    assert summary["merged_packages"] == 1
    assert "202203291830-export/borrow.csv" in filenames
    assert "202203291830-export/interest.csv" in filenames
    assert "202203291830-export/repay.csv" in filenames
    assert all("202203291730-export" not in name for name in filenames)
    assert superseded["package_row_status"] == "package_merge_into_primary"


def test_source_intake_service_keeps_different_cycle_packages_in_overlap_review(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    older = incoming_dir / "2021" / "Binance" / "202203291730-export"
    newer = incoming_dir / "2021" / "Binance" / "202203301830-export"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    borrow_payload = (
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    )
    interest_payload = "Pair,Coin,Amount,Time,Interest Type\nADA/USDT,USDT,0.1,2021-05-25 12:53:03,Hourly\n"
    repay_payload = (
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 13:53:03,0.0345,Auto repayment,CONFIRM\n"
    )
    (older / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    (older / "interest.csv").write_text(interest_payload, encoding="utf-8")
    (newer / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    (newer / "repay.csv").write_text(repay_payload, encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    SourceIntakeService(FilesystemArtifactStore()).plan(
        IntakePlanRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
        )
    )

    summary = json.loads((report_dir / "intake_summary.json").read_text(encoding="utf-8"))
    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    borrow_rows = [row for row in plan_rows if row["bundle_relative_path"] == "borrow.csv"]

    assert summary["merged_packages"] == 0
    assert summary["overlap_packages"] == 2
    assert all(row["package_status"] == "overlap_partial_review" for row in borrow_rows)
    assert all(row["review_required"] == "yes" for row in borrow_rows)
    assert all("package_overlap_review" in row["review_codes"] for row in borrow_rows)


def test_source_intake_service_marks_mixed_cycle_bundle_for_review_but_places_files(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    bundle_dir = incoming_dir / "2021" / "Binance" / "MixedCycle"
    bundle_dir.mkdir(parents=True)
    first_payload = (
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    )
    second_payload = (
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-26 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    )
    (bundle_dir / "202203291730-borrow.csv").write_text(first_payload, encoding="utf-8")
    (bundle_dir / "202203301730-repay.csv").write_text(second_payload, encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    SourceIntakeService(FilesystemArtifactStore()).apply(
        IntakeApplyRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
        )
    )

    summary = json.loads((report_dir / "intake_summary.json").read_text(encoding="utf-8"))
    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    mixed_rows = [row for row in plan_rows if row["bundle_id"] == "mixedcycle"]
    manifest_rows = FilesystemArtifactStore().read_rows(
        workspace_root / "evidence" / "raw" / "source" / "binance" / "2021-05" / "manifest.csv"
    )

    assert summary["mixed_cycle_packages"] == 1
    assert len(mixed_rows) == 2
    assert all(row["review_required"] == "yes" for row in mixed_rows)
    assert all("package_cycle_mixed" in row["review_codes"] for row in mixed_rows)
    assert len(manifest_rows) == 2
