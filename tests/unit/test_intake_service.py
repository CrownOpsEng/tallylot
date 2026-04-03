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
    assert any(row["action"] == "inspect_only" and row["archive_member_path"] == "inner.csv" for row in plan_rows)


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
