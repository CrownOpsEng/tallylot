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
