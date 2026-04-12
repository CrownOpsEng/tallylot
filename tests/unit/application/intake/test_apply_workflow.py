from __future__ import annotations

import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from tallylot.application.intake import (
    ApplyIntakeUseCase,
    IntakeApplyRequest,
    IntakePlanRequest,
    PlanIntakeUseCase,
)
from tallylot.application.resource_refs import to_resource_ref, to_workspace_path
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.captures import SOURCE_INVENTORY_HEADER
from tests.support.adapter_packs import fixture_raw_dir


def test_source_intake_service_applies_loose_files_into_workspace(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    source_file = incoming_dir / "transactions.csv"
    source_file.write_text("a,b\n1,2\n", encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    response = ApplyIntakeUseCase(build_registry(), FilesystemArtifactStore()).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )
    capture_label = summary["planned_capture_label"]
    target = (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "unclassified"
        / capture_label
        / "transactions.csv"
    )

    assert response.copied_count == 1
    assert target.exists()
    assert summary["copied_count"] == 1


def test_source_intake_service_applies_archive_members_into_workspace(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    archive_path = incoming_dir / "bundle.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("inner.csv", "a,b\n1,2\n")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    response = ApplyIntakeUseCase(build_registry(), FilesystemArtifactStore()).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    archive_target = (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "unclassified"
        / json.loads((report_dir / "intake_summary.json").read_text(encoding="utf-8"))[
            "planned_capture_label"
        ]
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
        / json.loads((report_dir / "intake_summary.json").read_text(encoding="utf-8"))[
            "planned_capture_label"
        ]
        / "bundle"
        / "contents"
        / "inner.csv"
    )

    assert response.copied_count == 2
    assert archive_target.exists()
    assert member_target.exists()


def test_source_intake_service_materializes_binance_statement_pdfs(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    for path in fixture_raw_dir("binance", "latest_statement_workbooks").iterdir():
        if path.is_file():
            shutil.copy2(path, incoming_dir / path.name)

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"
    artifacts = FilesystemArtifactStore()

    response = ApplyIntakeUseCase(build_registry(), artifacts).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )
    source_rows = artifacts.read_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )
    capture_root = (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "binance"
        / summary["planned_capture_label"]
    )

    assert response.copied_count == 5
    assert response.issue_count == 0
    assert summary["capture_status"] == "captured"
    assert capture_root.is_dir()
    assert (
        capture_root / "AccountStatementPeriod_fixtureacct_20240101-20241231_old.pdf"
    ).exists()
    assert (
        capture_root / "AccountStatementPeriod_fixtureacct_20250101-20251231_latest.pdf"
    ).exists()
    assert response.source == "binance"
    assert response.capture_status == "captured"
    assert response.copied_count == 5
    assert summary["source"] == "binance"
    assert summary["capture_status"] == "captured"
    assert summary["issue_count"] == 0
    assert summary["planned_copy_count"] == 5
    assert summary["copied_count"] == 5
    assert source_rows[0]["source"] == "binance"
    assert source_rows[0]["status"] == "capture_complete"
    assert source_rows[0]["capture_count"] == "1"
    assert source_rows[0]["latest_capture_label"] == summary["planned_capture_label"]


def test_source_intake_service_merges_same_cycle_near_duplicate_packages_on_apply(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    older = incoming_dir / "2021" / "Binance" / "202203291730-export"
    newer = incoming_dir / "2021" / "Binance" / "202203291830-export"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    borrow_payload = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    interest_payload = "Pair,Coin,Amount,Time,Interest Type\nADA/USDT,USDT,0.1,2021-05-25 12:53:03,Hourly\n"
    repay_payload = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 13:53:03,0.0345,Auto repayment,CONFIRM\n"
    (older / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    (older / "interest.csv").write_text(interest_payload, encoding="utf-8")
    (newer / "borrow.csv").write_text(borrow_payload, encoding="utf-8")
    (newer / "repay.csv").write_text(repay_payload, encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    ApplyIntakeUseCase(build_registry(), FilesystemArtifactStore()).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )
    capture_label = summary["planned_capture_label"]
    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    manifest_rows = FilesystemArtifactStore().read_rows(
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "binance"
        / capture_label
        / "manifest.csv"
    )
    filenames = {row["filename"] for row in manifest_rows}
    superseded = next(
        row
        for row in plan_rows
        if row["relative_path"].endswith("202203291730-export/borrow.csv")
    )

    assert summary["merge_primary_packages"] == 1
    assert summary["merged_packages"] == 1
    assert "202203291830-export/borrow.csv" in filenames
    assert "202203291830-export/interest.csv" in filenames
    assert "202203291830-export/repay.csv" in filenames
    assert all("202203291730-export" not in name for name in filenames)
    assert superseded["package_row_status"] == "package_merge_into_primary"


def test_source_intake_service_marks_mixed_cycle_bundle_for_review_but_places_files(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    bundle_dir = incoming_dir / "2021" / "Binance" / "MixedCycle"
    bundle_dir.mkdir(parents=True)
    first_payload = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    second_payload = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-26 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    (bundle_dir / "202203291730-borrow.csv").write_text(first_payload, encoding="utf-8")
    (bundle_dir / "202203301730-repay.csv").write_text(second_payload, encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    ApplyIntakeUseCase(build_registry(), FilesystemArtifactStore()).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )
    capture_label = summary["planned_capture_label"]
    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    mixed_rows = [row for row in plan_rows if row["bundle_id"] == "mixedcycle"]
    manifest_rows = FilesystemArtifactStore().read_rows(
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "binance"
        / capture_label
        / "manifest.csv"
    )

    assert summary["mixed_cycle_packages"] == 1
    assert len(mixed_rows) == 2
    assert all(row["review_required"] == "yes" for row in mixed_rows)
    assert all("package_cycle_mixed" in row["review_codes"] for row in mixed_rows)
    assert len(manifest_rows) == 2


def test_source_intake_service_applies_explicit_source_label_map(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    source_file = incoming_dir / "transactions.csv"
    source_file.write_text("a,b\n1,2\n", encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    issues_dir = workspace_root / "analysis" / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        issues_dir / "source_inventory.csv",
        ("source",),
        ({"source": "manual-main"},),
    )
    artifacts.write_rows(
        issues_dir / "source_label_map.csv",
        ("incoming_capture_scope", "incoming_path_prefix", "source", "notes"),
        (
            {
                "incoming_capture_scope": "",
                "incoming_path_prefix": ".",
                "source": "manual-main",
                "notes": "",
            },
        ),
    )
    report_dir = tmp_path / "reports"

    response = ApplyIntakeUseCase(build_registry(), artifacts).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    plan_rows = artifacts.read_rows(report_dir / "intake_plan.csv")
    summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )
    capture_label = summary["planned_capture_label"]
    target = (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "manual-main"
        / capture_label
        / "transactions.csv"
    )

    assert response.copied_count == 1
    assert target.exists()
    assert plan_rows[0]["source_resolution_status"] == "explicit_map"
    assert summary["explicit_map_count"] == 1


def test_source_intake_service_skips_blank_source_inventory_for_support_only_inputs(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    support_path = incoming_dir / "2021" / "Binance" / "note.png"
    support_path.parent.mkdir(parents=True, exist_ok=True)
    support_path.write_bytes(b"support")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"
    artifacts = FilesystemArtifactStore()

    response = ApplyIntakeUseCase(build_registry(), artifacts).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    plan_rows = artifacts.read_rows(report_dir / "intake_plan.csv")
    support_target = Path(plan_rows[0]["target_path"])

    assert response.copied_count == 1
    assert support_target.read_bytes() == b"support"
    assert not (
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    ).exists()
    assert not (
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    ).exists()


def test_source_intake_service_skips_rows_blocked_by_invalid_source_label_map(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    source_file = incoming_dir / "transactions.csv"
    source_file.write_text("a,b\n1,2\n", encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    issues_dir = workspace_root / "analysis" / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        issues_dir / "source_inventory.csv",
        ("source",),
        ({"source": "manual-main"},),
    )
    artifacts.write_rows(
        issues_dir / "source_label_map.csv",
        ("incoming_capture_scope", "incoming_path_prefix", "source", "notes"),
        (
            {
                "incoming_capture_scope": "",
                "incoming_path_prefix": ".",
                "source": "missing-source",
                "notes": "",
            },
        ),
    )
    report_dir = tmp_path / "reports"

    response = ApplyIntakeUseCase(build_registry(), artifacts).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    plan_rows = artifacts.read_rows(report_dir / "intake_plan.csv")
    issue_rows = artifacts.read_rows(report_dir / "intake_issues.csv")
    summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )

    assert response.copied_count == 0
    assert summary["capture_status"] == "capture_blocked"
    assert summary["planned_capture_label"] == ""
    assert summary["manifest_fingerprint"] == ""
    assert summary["file_count"] == 1
    assert plan_rows[0]["action"] == "skip"
    assert plan_rows[0]["placement_status"] == "mapping_blocked_skip"
    assert plan_rows[0]["source_resolution_status"] == "explicit_map_blocked"
    assert plan_rows[0]["review_codes"] == "source_map_unknown_source"
    assert plan_rows[0]["capture_status"] == "capture_blocked"
    assert not (
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    ).exists()
    assert artifacts.read_rows(issues_dir / "source_inventory.csv") == [
        {"source": "manual-main"}
    ]
    assert summary["explicit_map_blocked_count"] == 1
    assert summary["source_label_map_issue_count"] == 1
    assert issue_rows[0]["kind"] == "source_label_map_unknown_source"


def test_source_intake_service_applies_scoped_dot_mappings_for_multiple_sources(
    tmp_path: Path,
) -> None:
    incoming_a = tmp_path / "incoming" / "bsc-stage"
    incoming_b = tmp_path / "incoming" / "eth-stage"
    incoming_a.mkdir(parents=True)
    incoming_b.mkdir(parents=True)
    (incoming_a / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (incoming_b / "transactions.csv").write_text("a,b\n3,4\n", encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    issues_dir = workspace_root / "analysis" / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        issues_dir / "source_inventory.csv",
        ("source",),
        ({"source": "bsc-main"}, {"source": "eth-main"}),
    )
    artifacts.write_rows(
        issues_dir / "source_label_map.csv",
        ("incoming_capture_scope", "incoming_path_prefix", "source", "notes"),
        (
            {
                "incoming_capture_scope": "bsc-stage",
                "incoming_path_prefix": ".",
                "source": "bsc-main",
                "notes": "",
            },
            {
                "incoming_capture_scope": "eth-stage",
                "incoming_path_prefix": ".",
                "source": "eth-main",
                "notes": "",
            },
        ),
    )
    report_a = tmp_path / "reports-a"
    report_b = tmp_path / "reports-b"

    response_a = ApplyIntakeUseCase(build_registry(), artifacts).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_a),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_a),
        )
    )
    response_b = ApplyIntakeUseCase(build_registry(), artifacts).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_b),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_b),
        )
    )

    summary_a = json.loads(
        (report_a / "intake_summary.json").read_text(encoding="utf-8")
    )
    summary_b = json.loads(
        (report_b / "intake_summary.json").read_text(encoding="utf-8")
    )

    assert response_a.copied_count == 1
    assert response_b.copied_count == 1
    assert (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "bsc-main"
        / summary_a["planned_capture_label"]
        / "transactions.csv"
    ).exists()
    assert (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "eth-main"
        / summary_b["planned_capture_label"]
        / "transactions.csv"
    ).exists()


def test_source_intake_service_reuses_planned_capture_label_on_apply(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    (incoming_dir / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"
    artifacts = FilesystemArtifactStore()

    PlanIntakeUseCase(build_registry(), artifacts).execute(
        IntakePlanRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )
    planned_label = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )["planned_capture_label"]

    ApplyIntakeUseCase(build_registry(), artifacts).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )
    applied_summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )

    assert applied_summary["planned_capture_label"] == planned_label


def test_source_intake_service_does_not_merge_new_capture_into_stale_report_label(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"
    artifacts = FilesystemArtifactStore()
    service = ApplyIntakeUseCase(build_registry(), artifacts)

    first_incoming = tmp_path / "incoming-1"
    first_incoming.mkdir()
    (first_incoming / "first.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    service.execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(first_incoming),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )
    first_summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )

    second_incoming = tmp_path / "incoming-2"
    second_incoming.mkdir()
    (second_incoming / "second.csv").write_text("a,b\n3,4\n", encoding="utf-8")

    service.execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(second_incoming),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )
    second_summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )

    source_root = workspace_root / "evidence" / "raw" / "source" / "unclassified"

    assert (
        second_summary["planned_capture_label"]
        != first_summary["planned_capture_label"]
    )
    assert (source_root / first_summary["planned_capture_label"] / "first.csv").exists()
    assert not (
        source_root / first_summary["planned_capture_label"] / "second.csv"
    ).exists()
    assert (
        source_root / second_summary["planned_capture_label"] / "second.csv"
    ).exists()


def test_source_intake_service_blocks_duplicate_capture_by_manifest_fingerprint(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    (incoming_dir / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    workspace_root = tmp_path / "workspace"
    first_report_dir = tmp_path / "reports-1"
    second_report_dir = tmp_path / "reports-2"
    artifacts = FilesystemArtifactStore()
    service = ApplyIntakeUseCase(build_registry(), artifacts)

    service.execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(first_report_dir),
        )
    )
    first_summary = json.loads(
        (first_report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )

    service.execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(second_report_dir),
        )
    )
    second_summary = json.loads(
        (second_report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )
    capture_rows = artifacts.read_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    )

    assert second_summary["capture_status"] == "duplicate_blocked"
    assert second_summary["duplicate_capture_uid"] == capture_rows[0]["capture_uid"]
    assert not (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "unclassified"
        / second_summary["planned_capture_label"]
    ).exists()
    assert capture_rows[0]["capture_label"] == first_summary["planned_capture_label"]
    assert capture_rows[1]["status"] == "duplicate_blocked"
    assert capture_rows[1]["capture_root_ref"] == ""
    assert capture_rows[1]["incoming_ref"] == "incoming/incoming"
    assert capture_rows[1]["file_count"] == "1"
    assert capture_rows[1]["intake_started_at"] != ""
    assert capture_rows[1]["intake_completed_at"] != ""


def test_duplicate_blocked_apply_does_not_overwrite_supporting_artifacts(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    issues_dir = workspace_root / "analysis" / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        issues_dir / "source_inventory.csv",
        ("source",),
        ({"source": "manual-main"},),
    )
    artifacts.write_rows(
        issues_dir / "source_label_map.csv",
        ("incoming_capture_scope", "incoming_path_prefix", "source", "notes"),
        (
            {
                "incoming_capture_scope": "",
                "incoming_path_prefix": ".",
                "source": "manual-main",
                "notes": "",
            },
        ),
    )
    service = ApplyIntakeUseCase(build_registry(), artifacts)
    support_filename = "Binance Portfolio Notes.xlsx"

    first_incoming = tmp_path / "incoming-1"
    first_incoming.mkdir()
    (first_incoming / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (first_incoming / support_filename).write_bytes(b"first-support")

    service.execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(first_incoming),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(tmp_path / "reports-1"),
        )
    )

    first_plan_rows = artifacts.read_rows(tmp_path / "reports-1" / "intake_plan.csv")
    support_target = Path(
        next(
            row["target_path"]
            for row in first_plan_rows
            if row["relative_path"] == support_filename
        )
    )
    assert support_target.read_bytes() == b"first-support"

    second_incoming = tmp_path / "incoming-2"
    second_incoming.mkdir()
    (second_incoming / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (second_incoming / support_filename).write_bytes(b"second-support")

    service.execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(second_incoming),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(tmp_path / "reports-2"),
        )
    )

    second_summary = json.loads(
        (tmp_path / "reports-2" / "intake_summary.json").read_text(encoding="utf-8")
    )
    second_plan_rows = artifacts.read_rows(tmp_path / "reports-2" / "intake_plan.csv")
    second_support_row = next(
        row for row in second_plan_rows if row["relative_path"] == support_filename
    )
    second_source_row = next(
        row for row in second_plan_rows if row["relative_path"] == "transactions.csv"
    )

    assert second_summary["capture_status"] == "duplicate_blocked"
    assert second_summary["copied_count"] == 0
    assert second_summary["planned_copy_count"] == 0
    assert second_support_row["action"] == "skip"
    assert second_support_row["capture_status"] == "duplicate_blocked"
    assert second_source_row["action"] == "skip"
    assert support_target.read_bytes() == b"first-support"


def test_capture_blocked_apply_avoids_materialized_writes_and_source_mutation(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    issues_dir = workspace_root / "analysis" / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    artifacts = FilesystemArtifactStore()
    source_rows = (
        {
            "source": "binance-main",
            "activity_after_cutoff": "",
            "scope_status": "",
            "status": "",
            "capture_count": "",
            "latest_capture_uid": "",
            "latest_capture_label": "",
            "latest_capture_completed_at": "",
            "assembly_status": "",
            "assembled_root_ref": "",
            "adapter_hints": "",
            "notes": "",
        },
        {
            "source": "coinbase-main",
            "activity_after_cutoff": "",
            "scope_status": "",
            "status": "",
            "capture_count": "",
            "latest_capture_uid": "",
            "latest_capture_label": "",
            "latest_capture_completed_at": "",
            "assembly_status": "",
            "assembled_root_ref": "",
            "adapter_hints": "",
            "notes": "",
        },
    )
    artifacts.write_rows(
        issues_dir / "source_inventory.csv",
        SOURCE_INVENTORY_HEADER,
        source_rows,
    )
    artifacts.write_rows(
        issues_dir / "source_label_map.csv",
        ("incoming_capture_scope", "incoming_path_prefix", "source", "notes"),
        (
            {
                "incoming_capture_scope": "",
                "incoming_path_prefix": "binance",
                "source": "binance-main",
                "notes": "",
            },
            {
                "incoming_capture_scope": "",
                "incoming_path_prefix": "coinbase",
                "source": "coinbase-main",
                "notes": "",
            },
        ),
    )
    incoming_dir = tmp_path / "incoming"
    (incoming_dir / "binance").mkdir(parents=True)
    (incoming_dir / "coinbase").mkdir(parents=True)
    (incoming_dir / "binance" / "transactions.csv").write_text(
        "a,b\n1,2\n", encoding="utf-8"
    )
    (incoming_dir / "coinbase" / "transactions.csv").write_text(
        "a,b\n3,4\n", encoding="utf-8"
    )
    (incoming_dir / "binance" / "notes.png").write_bytes(b"support")

    response = ApplyIntakeUseCase(build_registry(), artifacts).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(tmp_path / "reports"),
        )
    )

    summary = json.loads(
        (tmp_path / "reports" / "intake_summary.json").read_text(encoding="utf-8")
    )
    plan_rows = artifacts.read_rows(tmp_path / "reports" / "intake_plan.csv")
    updated_source_rows = artifacts.read_rows(issues_dir / "source_inventory.csv")
    support_row = next(
        row for row in plan_rows if row["relative_path"] == "binance/notes.png"
    )
    source_row = next(
        row for row in plan_rows if row["relative_path"] == "binance/transactions.csv"
    )
    support_target = Path(support_row["target_path"])

    assert response.source == ""
    assert summary["capture_status"] == "capture_blocked"
    assert response.copied_count == 1
    assert summary["copied_count"] == 1
    assert summary["planned_copy_count"] == 1
    assert summary["file_count"] == 2
    assert support_row["action"] == "copy"
    assert support_row["capture_status"] == "capture_blocked"
    assert support_row["review_codes"] == "mixed_source_capture"
    assert source_row["capture_label"] == ""
    assert support_target.read_bytes() == b"support"
    assert not (
        workspace_root
        / "working"
        / "supporting_artifacts"
        / "binance-main"
        / "incoming"
        / "notes.png"
    ).exists()
    assert not (
        workspace_root / "evidence" / "raw" / "source" / "binance-main" / "capture.json"
    ).exists()
    assert not (
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    ).exists()
    assert updated_source_rows == list(source_rows)


def test_support_only_apply_reports_missing_source_raw_issue(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    (incoming_dir / "notes.png").write_bytes(b"support-only")
    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"
    artifacts = FilesystemArtifactStore()

    response = ApplyIntakeUseCase(build_registry(), artifacts).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )
    issue_rows = artifacts.read_rows(report_dir / "intake_issues.csv")
    plan_rows = artifacts.read_rows(report_dir / "intake_plan.csv")

    assert response.capture_status == "capture_blocked"
    assert response.issue_count == 1
    assert response.copied_count == 1
    assert summary["issue_count"] == 1
    assert summary["copied_count"] == 1
    assert summary["planned_copy_count"] == 1
    assert issue_rows[0]["kind"] == "capture_missing_source_raw"
    assert plan_rows[0]["action"] == "copy"
    assert plan_rows[0]["review_required"] == "yes"
    assert plan_rows[0]["review_codes"] == "missing_source_raw_capture"
    assert Path(plan_rows[0]["target_path"]).exists()
    assert not (
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    ).exists()


def test_source_intake_service_marks_overlapping_capture_for_review(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    first_incoming = tmp_path / "incoming-1"
    second_incoming = tmp_path / "incoming-2"
    first_incoming.mkdir()
    second_incoming.mkdir()
    payload_a = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    payload_b = "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0500,Auto borrowing,CONFIRM\n"
    (first_incoming / "borrow.csv").write_text(payload_a, encoding="utf-8")
    (second_incoming / "borrow.csv").write_text(payload_b, encoding="utf-8")
    artifacts = FilesystemArtifactStore()
    service = ApplyIntakeUseCase(build_registry(), artifacts)

    service.execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(first_incoming),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(tmp_path / "reports-1"),
        )
    )
    service.execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(second_incoming),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(tmp_path / "reports-2"),
        )
    )

    second_summary = json.loads(
        (tmp_path / "reports-2" / "intake_summary.json").read_text(encoding="utf-8")
    )
    capture_rows = artifacts.read_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    )

    assert second_summary["capture_status"] == "overlap_review_required"
    assert capture_rows[-1]["status"] == "overlap_review_required"


def test_source_inventory_summary_updates_after_apply(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    (incoming_dir / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"
    artifacts = FilesystemArtifactStore()

    ApplyIntakeUseCase(build_registry(), artifacts).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )
    source_rows = artifacts.read_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )

    assert source_rows == [
        {
            "source": "unclassified",
            "activity_after_cutoff": "",
            "scope_status": "in_scope",
            "status": "capture_complete",
            "capture_count": "1",
            "latest_capture_uid": source_rows[0]["latest_capture_uid"],
            "latest_capture_label": summary["planned_capture_label"],
            "latest_capture_completed_at": source_rows[0][
                "latest_capture_completed_at"
            ],
            "assembly_status": "pending",
            "assembled_root_ref": "",
            "adapter_hints": "",
            "notes": "",
        }
    ]


def test_apply_summary_reports_captured_status_for_materialized_capture(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    (incoming_dir / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    response = ApplyIntakeUseCase(build_registry(), FilesystemArtifactStore()).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )

    assert response.capture_status == "captured"
    assert summary["capture_status"] == "captured"


def test_new_capture_clears_stale_assembly_state_for_existing_source(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    issues_dir = workspace_root / "analysis" / "issues"
    inventory_dir = workspace_root / "analysis" / "inventory"
    issues_dir.mkdir(parents=True, exist_ok=True)
    inventory_dir.mkdir(parents=True, exist_ok=True)
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        issues_dir / "source_inventory.csv",
        SOURCE_INVENTORY_HEADER,
        (
            {
                "source": "manual-main",
                "activity_after_cutoff": "",
                "scope_status": "in_scope",
                "status": "assembled",
                "capture_count": "1",
                "latest_capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "latest_capture_label": "2026-03-23T14-15-16Z",
                "latest_capture_completed_at": "2026-03-23 14:15:16",
                "assembly_status": "assembled",
                "assembled_root_ref": "working/normalized/sources/manual-main",
                "adapter_hints": "",
                "notes": "",
            },
        ),
    )
    artifacts.write_rows(
        inventory_dir / "source_captures.csv",
        (
            "capture_uid",
            "source",
            "capture_label",
            "status",
            "intake_started_at",
            "intake_completed_at",
            "intake_method",
            "incoming_ref",
            "capture_root_ref",
            "manifest_fingerprint",
            "file_count",
            "observed_period_start",
            "observed_period_end",
            "observed_group_count",
            "supersedes_capture_uid",
            "notes",
        ),
        (
            {
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "source": "manual-main",
                "capture_label": "2026-03-23T14-15-16Z",
                "status": "assembly_included",
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/manual-main",
                "capture_root_ref": "evidence/raw/source/manual-main/2026-03-23T14-15-16Z",
                "manifest_fingerprint": "manifest:existing",
                "file_count": "1",
                "observed_period_start": "2026-03-23",
                "observed_period_end": "2026-03-23",
                "observed_group_count": "1",
                "supersedes_capture_uid": "",
                "notes": "",
            },
        ),
    )
    artifacts.write_rows(
        issues_dir / "source_label_map.csv",
        ("incoming_capture_scope", "incoming_path_prefix", "source", "notes"),
        (
            {
                "incoming_capture_scope": "",
                "incoming_path_prefix": ".",
                "source": "manual-main",
                "notes": "",
            },
        ),
    )
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    (incoming_dir / "transactions.csv").write_text("a,b\n3,4\n", encoding="utf-8")

    ApplyIntakeUseCase(build_registry(), artifacts).execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(tmp_path / "reports"),
        )
    )

    summary = json.loads(
        (tmp_path / "reports" / "intake_summary.json").read_text(encoding="utf-8")
    )
    updated_rows = artifacts.read_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )

    assert updated_rows == [
        {
            "source": "manual-main",
            "activity_after_cutoff": "",
            "scope_status": "in_scope",
            "status": "normalized",
            "capture_count": "2",
            "latest_capture_uid": updated_rows[0]["latest_capture_uid"],
            "latest_capture_label": summary["planned_capture_label"],
            "latest_capture_completed_at": updated_rows[0][
                "latest_capture_completed_at"
            ],
            "assembly_status": "pending",
            "assembled_root_ref": "",
            "adapter_hints": "",
            "notes": "",
        }
    ]


def test_source_inventory_summary_does_not_regress_after_duplicate_blocked_attempt(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    (incoming_dir / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    service = ApplyIntakeUseCase(build_registry(), artifacts)

    service.execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(tmp_path / "reports-1"),
        )
    )
    source_rows = artifacts.read_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )
    source_rows[0]["status"] = "normalized"
    artifacts.write_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv",
        tuple(source_rows[0].keys()),
        source_rows,
    )

    service.execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(tmp_path / "reports-2"),
        )
    )

    updated_rows = artifacts.read_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )

    assert updated_rows[0]["status"] == "normalized"
    assert updated_rows[0]["capture_count"] == "2"
