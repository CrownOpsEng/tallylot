from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.intake import ScannedFile
from crypto_reconciliation.application.intake.file_facts import IntakeFileFacts
from crypto_reconciliation.application.intake.routing import route_intake_file
from crypto_reconciliation.infrastructure.discovery import build_registry


def test_route_intake_file_routes_archive_members_under_contents_tree(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    bundle_path = incoming_dir / "bundle.zip"
    bundle_path.write_text("fixture", encoding="utf-8")
    workspace_root = tmp_path / "workspace"

    route = route_intake_file(
        ScannedFile(
            relative_path="bundle.zip::inner.csv",
            file_path=bundle_path,
            size_bytes=bundle_path.stat().st_size,
            sha256="fixture",
            archive_source_path="bundle.zip",
            archive_member_path="inner.csv",
        ),
        registry=build_registry(),
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(header=("Timestamp",)),
    )

    assert route.category == "source_raw"
    assert route.action == "extract_copy"
    assert route.target_path == (workspace_root / "evidence/raw/source/unclassified/incoming/bundle/contents/inner.csv")


def test_route_intake_file_routes_working_derivatives_to_supporting_artifacts(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    derivative_path = incoming_dir / "trade Analysis - ADA-USDT - Binance.png"
    incoming_dir.mkdir()
    derivative_path.write_bytes(b"png")
    workspace_root = tmp_path / "workspace"

    route = route_intake_file(
        ScannedFile(
            relative_path=derivative_path.name,
            file_path=derivative_path,
            size_bytes=derivative_path.stat().st_size,
            sha256="fixture",
        ),
        registry=build_registry(),
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(),
    )

    assert route.category == "supporting_artifact"
    assert route.role == "working_derivative"
    assert route.source_folder == "binance"
    assert route.target_path == (
        workspace_root / "working/supporting_artifacts/binance/incoming/trade Analysis - ADA-USDT - Binance.png"
    )


def test_route_intake_file_routes_generic_supporting_artifacts_when_suffix_is_not_raw_or_derivative(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    note_path = incoming_dir / "capture-notes.txt"
    note_path.write_text("notes", encoding="utf-8")
    workspace_root = tmp_path / "workspace"

    route = route_intake_file(
        ScannedFile(
            relative_path=note_path.name,
            file_path=note_path,
            size_bytes=note_path.stat().st_size,
            sha256="fixture",
        ),
        registry=build_registry(),
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(),
    )

    assert route.category == "supporting_artifact"
    assert route.role == "supporting_artifact"
    assert route.source_folder == "unclassified"


def test_route_intake_file_uses_header_hints_for_loose_source_exports(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    export_path = incoming_dir / "borrow.csv"
    export_path.write_text(
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n",
        encoding="utf-8",
    )
    workspace_root = tmp_path / "workspace"

    route = route_intake_file(
        ScannedFile(
            relative_path=export_path.name,
            file_path=export_path,
            size_bytes=export_path.stat().st_size,
            sha256="fixture",
        ),
        registry=build_registry(),
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(
            header=("Pair", "Coin", "Date", "Amount", "Type", "Status"),
            min_timestamp="2021-05-25 12:53:03",
        ),
    )

    assert route.category == "source_raw"
    assert route.source_folder == "binance"
    assert route.capture_id == "2021-05"
    assert route.target_path == workspace_root / "evidence/raw/source/binance/2021-05/borrow.csv"


def test_route_intake_file_routes_zip_archives_under_archive_tree(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    archive_path = incoming_dir / "202203291736.zip"
    archive_path.write_bytes(b"PK\x03\x04")
    workspace_root = tmp_path / "workspace"

    route = route_intake_file(
        ScannedFile(
            relative_path=archive_path.name,
            file_path=archive_path,
            size_bytes=archive_path.stat().st_size,
            sha256="fixture",
        ),
        registry=build_registry(),
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(header=("Date(UTC)", "Pair", "Side", "Price", "Executed", "Amount", "Fee")),
    )

    assert route.category == "source_raw"
    assert route.capture_id == "2022-03"
    assert route.target_path == (
        workspace_root / "evidence/raw/source/binance/2022-03/202203291736/archive/202203291736.zip"
    )
