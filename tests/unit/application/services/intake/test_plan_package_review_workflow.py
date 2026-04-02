from __future__ import annotations

import json
from pathlib import Path

from crypto_reconciliation.application.dtos import IntakePlanRequest
from crypto_reconciliation.application.services.intake import SourceIntakeService
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore


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
