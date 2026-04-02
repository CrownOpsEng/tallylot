from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from crypto_reconciliation.application.intake import ApplyIntakeUseCase, IntakeApplyRequest
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_source_intake_service_applies_loose_files_into_workspace(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    source_file = incoming_dir / "transactions.csv"
    source_file.write_text("a,b\n1,2\n", encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    response = ApplyIntakeUseCase(build_registry(), FilesystemArtifactStore()).execute(
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

    response = ApplyIntakeUseCase(build_registry(), FilesystemArtifactStore()).execute(
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

    ApplyIntakeUseCase(build_registry(), FilesystemArtifactStore()).execute(
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

    ApplyIntakeUseCase(build_registry(), FilesystemArtifactStore()).execute(
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
