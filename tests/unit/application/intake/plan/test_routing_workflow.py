from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from tallylot.application.intake import IntakePlanRequest, PlanIntakeUseCase
from tallylot.application.resource_refs import to_resource_ref, to_workspace_path
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.evidence import EVIDENCE_PROVENANCE_HEADER


def test_source_intake_service_plans_archive_members_without_copying_them(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    archive_path = incoming_dir / "bundle.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("inner.csv", "a,b\n1,2\n")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    response = PlanIntakeUseCase(build_registry(), FilesystemArtifactStore()).execute(
        IntakePlanRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")

    assert response.file_count == 2
    assert any(
        row["action"] == "copy" and row["path"].endswith("bundle.zip")
        for row in plan_rows
    )
    assert any(
        row["action"] == "extract_copy" and row["archive_member_path"] == "inner.csv"
        for row in plan_rows
    )


def test_source_intake_service_routes_source_artifacts_to_source_aware_supporting_paths(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    image_path = (
        incoming_dir
        / "2021"
        / "Binance"
        / "From Binance"
        / "trade Analysis - ADA-USDT - Binance.png"
    )
    scratch_csv = incoming_dir / "2021" / "Binance" / "2021 Isolated" / "test.csv"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    scratch_csv.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"png")
    scratch_csv.write_text("a,b\n1,2\n", encoding="utf-8")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    PlanIntakeUseCase(build_registry(), FilesystemArtifactStore()).execute(
        IntakePlanRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    by_name = {
        Path(row["path"]).name: row
        for row in plan_rows
        if not row["archive_member_path"]
    }

    assert (
        by_name["trade Analysis - ADA-USDT - Binance.png"]["role"]
        == "working_derivative"
    )
    assert (
        by_name["trade Analysis - ADA-USDT - Binance.png"]["source_folder"] == "binance"
    )
    assert (
        "/working/supporting_artifacts/binance/"
        in by_name["trade Analysis - ADA-USDT - Binance.png"]["target_path"]
    )
    assert by_name["test.csv"]["role"] == "working_derivative"
    assert (
        "/working/supporting_artifacts/binance/" in by_name["test.csv"]["target_path"]
    )


def test_source_intake_service_routes_binance_upstream_workbooks_to_raw_capture(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    order_workbook = incoming_dir / "Binance Order History 2023.xlsx"
    withdrawal_workbook = incoming_dir / "Binance-Withdrawal History Report 2023.xlsx"
    notes_workbook = incoming_dir / "Binance Portfolio Notes.xlsx"
    order_workbook.write_bytes(b"PK\x03\x04")
    withdrawal_workbook.write_bytes(b"PK\x03\x04")
    notes_workbook.write_bytes(b"PK\x03\x04")

    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"
    artifacts = FilesystemArtifactStore()

    response = PlanIntakeUseCase(build_registry(), artifacts).execute(
        IntakePlanRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    by_name = {
        Path(row["path"]).name: row
        for row in artifacts.read_rows(report_dir / "intake_plan.csv")
    }

    assert response.file_count == 3
    assert response.planned_copy_count == 3
    assert by_name["Binance Order History 2023.xlsx"]["category"] == "source_raw"
    assert by_name["Binance Order History 2023.xlsx"]["role"] == "source_export"
    assert (
        by_name["Binance Order History 2023.xlsx"]["evidence_role"]
        == "transaction_source"
    )
    assert (
        by_name["Binance Order History 2023.xlsx"]["originality_class"]
        == "upstream_original"
    )
    assert by_name["Binance Order History 2023.xlsx"]["capture_label"] != ""
    assert (
        "/evidence/raw/source/binance/"
        in by_name["Binance Order History 2023.xlsx"]["target_path"]
    )
    assert by_name["Binance Order History 2023.xlsx"]["target_path"].endswith(
        "/Binance Order History 2023.xlsx"
    )
    assert (
        by_name["Binance-Withdrawal History Report 2023.xlsx"]["category"]
        == "source_raw"
    )
    assert (
        by_name["Binance-Withdrawal History Report 2023.xlsx"]["originality_class"]
        == "upstream_original"
    )
    assert by_name["Binance Portfolio Notes.xlsx"]["category"] == "supporting_artifact"
    assert by_name["Binance Portfolio Notes.xlsx"]["role"] == "working_derivative"
    assert (
        by_name["Binance Portfolio Notes.xlsx"]["evidence_role"]
        == "supporting_artifact"
    )
    assert (
        by_name["Binance Portfolio Notes.xlsx"]["originality_class"]
        == "operator_authored"
    )


def test_source_intake_service_routes_cointracking_html_and_sidecar_to_portfolio_capture(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    html_path = incoming_dir / "tmp" / "CoinTracking · Tax Declaration Export.html"
    sidecar_path = (
        incoming_dir
        / "tmp"
        / "CoinTracking · Tax Declaration Export_files"
        / "style.min.css"
    )
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

    PlanIntakeUseCase(build_registry(), FilesystemArtifactStore()).execute(
        IntakePlanRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    by_name = {Path(row["path"]).name: row for row in plan_rows}

    assert (
        by_name["CoinTracking · Tax Declaration Export.html"]["role"]
        == "portfolio_export"
    )
    assert (
        by_name["CoinTracking · Tax Declaration Export.html"]["capture_label"]
        == "2022-04"
    )
    assert (
        "/evidence/raw/portfolio/cointracking/2022-04/"
        in by_name["CoinTracking · Tax Declaration Export.html"]["target_path"]
    )
    assert by_name["style.min.css"]["role"] == "portfolio_sidecar"
    assert by_name["style.min.css"]["capture_label"] == "2022-04"


def test_source_intake_service_routes_wallet_export_to_existing_inventory_source(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    source_inventory_path = (
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )
    source_inventory_path.parent.mkdir(parents=True, exist_ok=True)
    FilesystemArtifactStore().write_rows(
        source_inventory_path,
        (
            "source",
            "activity_after_cutoff",
            "scope_status",
            "status",
            "capture_count",
            "latest_capture_uid",
            "latest_capture_label",
            "latest_capture_completed_at",
            "assembly_status",
            "assembled_root_ref",
            "adapter_hints",
            "notes",
        ),
        (
            {
                "source": "eth-wallet-fixture",
                "activity_after_cutoff": "unknown",
                "scope_status": "in_scope",
                "status": "capture_complete",
                "capture_count": "1",
                "latest_capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "latest_capture_label": "2026-03-23T14-15-16Z",
                "latest_capture_completed_at": "2026-03-23 14:15:16",
                "assembly_status": "assembled",
                "assembled_root_ref": "working/normalized/sources/eth-wallet-fixture",
                "adapter_hints": "evm_explorer",
                "notes": "",
            },
        ),
    )
    location_evidence_path = (
        workspace_root / "analysis" / "inventory" / "location_inventory_evidence.csv"
    )
    location_evidence_path.parent.mkdir(parents=True, exist_ok=True)
    FilesystemArtifactStore().write_rows(
        location_evidence_path,
        (
            "source",
            "capture_uid",
            "capture_label",
            "capture_root_ref",
            "location_id",
            "location_kind",
            "location_label",
            "parent_location_id",
            "location_path",
            "identifier_kind",
            "normalized_identifier",
            "display_identifier",
            "network_scope",
            "controller",
            "parent_location_label",
            "evidence_kind",
            *EVIDENCE_PROVENANCE_HEADER,
            "confidence",
            "note",
        ),
        (
            {
                "source": "eth-wallet-fixture",
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "capture_label": "2026-03-23T14-15-16Z",
                "capture_root_ref": "evidence/raw/source/eth-wallet-fixture/2026-03-23T14-15-16Z",
                "location_id": "evm_address:0x2222222222222222222222222222222222222222",
                "location_kind": "onchain_address",
                "location_label": "Wallet 2",
                "parent_location_id": "",
                "location_path": "Wallet 2",
                "identifier_kind": "evm_address",
                "normalized_identifier": "0x2222222222222222222222222222222222222222",
                "display_identifier": "0x2222222222222222222222222222222222222222",
                "network_scope": "ethereum",
                "controller": "Explorer export",
                "parent_location_label": "",
                "evidence_kind": "filename",
                "evidence_capture_uid": "",
                "evidence_relative_path": "/tmp/evidence.csv",
                "evidence_archive_member_path": "",
                "evidence_locator_kind": "raw_file",
                "evidence_anchor": "",
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

    PlanIntakeUseCase(build_registry(), FilesystemArtifactStore()).execute(
        IntakePlanRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    row = next(item for item in plan_rows if item["archive_member_path"] == "")

    assert row["source_folder"] == "eth-wallet-fixture"
    assert row["inventory_match_status"] == "inventory_source_match"
    assert row["review_required"] == "no"


def test_source_intake_service_uses_explicit_source_label_map_for_stable_source_labels(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    issues_dir = workspace_root / "analysis" / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        issues_dir / "source_inventory.csv",
        ("source",),
        ({"source": "binance-main"},),
    )
    artifacts.write_rows(
        issues_dir / "source_label_map.csv",
        ("incoming_path_prefix", "source", "notes"),
        (
            {
                "incoming_path_prefix": "2021/Binance",
                "source": "binance-main",
                "notes": "",
            },
        ),
    )
    incoming_dir = tmp_path / "incoming"
    image_path = (
        incoming_dir
        / "2021"
        / "Binance"
        / "From Binance"
        / "trade Analysis - ADA-USDT - Binance.png"
    )
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"png")
    report_dir = tmp_path / "reports"

    PlanIntakeUseCase(build_registry(), artifacts).execute(
        IntakePlanRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
        )
    )

    row = next(
        item
        for item in artifacts.read_rows(report_dir / "intake_plan.csv")
        if item["archive_member_path"] == ""
    )

    assert row["source_folder"] == "binance-main"
    assert row["source_resolution_status"] == "explicit_map"
    assert row["inventory_match_status"] == "not_evaluated_explicit_map"
    assert "/working/supporting_artifacts/binance-main/" in row["target_path"]
