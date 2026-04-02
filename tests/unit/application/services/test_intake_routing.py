from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.services.archive_scan import ScannedFile
from crypto_reconciliation.application.services.intake_file_facts import IntakeFileFacts
from crypto_reconciliation.application.services.intake_routing import route_intake_file


def test_route_intake_file_routes_cointracking_pdf_to_portfolio_capture(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    pdf_path = incoming_dir / "CoinTracking - 2021 Tax Export - Summary.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    workspace_root = tmp_path / "workspace"

    route = route_intake_file(
        ScannedFile(
            relative_path=pdf_path.name,
            file_path=pdf_path,
            size_bytes=pdf_path.stat().st_size,
            sha256="fixture",
        ),
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(),
    )

    assert route.category == "portfolio_raw"
    assert route.role == "portfolio_export"
    assert route.capture_id == "2021"
    assert route.target_path == (
        workspace_root / "evidence/raw/portfolio/cointracking/2021/CoinTracking - 2021 Tax Export - Summary.pdf"
    )


def test_route_intake_file_routes_cointracking_sidecar_by_html_export_timestamp(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    sidecar_dir = incoming_dir / "CoinTracking Export_files"
    sidecar_dir.mkdir(parents=True)
    html_path = incoming_dir / "CoinTracking Export.html"
    html_path.write_text(
        "<html><body>Created by: CoinTracking as of: 06.04.2022 01:11</body></html>",
        encoding="utf-8",
    )
    sidecar_path = sidecar_dir / "style.min.css"
    sidecar_path.write_text("body{}", encoding="utf-8")
    workspace_root = tmp_path / "workspace"

    route = route_intake_file(
        ScannedFile(
            relative_path="CoinTracking Export_files/style.min.css",
            file_path=sidecar_path,
            size_bytes=sidecar_path.stat().st_size,
            sha256="fixture",
        ),
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(),
    )

    assert route.category == "portfolio_raw"
    assert route.role == "portfolio_sidecar"
    assert route.capture_id == "2022-04"
    assert route.target_path == (
        workspace_root / "evidence/raw/portfolio/cointracking/2022-04/CoinTracking Export_files/style.min.css"
    )


def test_route_intake_file_routes_cointracking_sidecar_to_unknown_capture_without_html(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    sidecar_dir = incoming_dir / "CoinTracking Export_files"
    sidecar_dir.mkdir(parents=True)
    sidecar_path = sidecar_dir / "style.min.css"
    sidecar_path.write_text("body{}", encoding="utf-8")
    workspace_root = tmp_path / "workspace"

    route = route_intake_file(
        ScannedFile(
            relative_path="CoinTracking Export_files/style.min.css",
            file_path=sidecar_path,
            size_bytes=sidecar_path.stat().st_size,
            sha256="fixture",
        ),
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(),
    )

    assert route.category == "portfolio_raw"
    assert route.capture_id == "unknown"


def test_route_intake_file_routes_archive_sidecar_by_archive_capture_id(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    archive_path = incoming_dir / "CoinTracking-202203.zip"
    archive_path.write_bytes(b"PK\x03\x04")
    workspace_root = tmp_path / "workspace"

    route = route_intake_file(
        ScannedFile(
            relative_path="CoinTracking-202203.zip::CoinTracking Export_files/style.min.css",
            file_path=archive_path,
            size_bytes=archive_path.stat().st_size,
            sha256="fixture",
            archive_source_path="CoinTracking-202203.zip",
            archive_member_path="CoinTracking Export_files/style.min.css",
        ),
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(),
    )

    assert route.category == "portfolio_raw"
    assert route.role == "portfolio_sidecar"
    assert route.capture_id == "2022-03"


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
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(header=("Timestamp",)),
    )

    assert route.category == "source_raw"
    assert route.action == "extract_copy"
    assert route.target_path == (workspace_root / "evidence/raw/source/unclassified/incoming/bundle/contents/inner.csv")


def test_route_intake_file_routes_working_derivatives_to_supporting_artifacts(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    derivative_path = incoming_dir / "Trade Analysis - ADA-USDT - Binance.png"
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
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(),
    )

    assert route.category == "supporting_artifact"
    assert route.role == "working_derivative"
    assert route.source_folder == "binance"
    assert route.target_path == (
        workspace_root / "working/supporting_artifacts/binance/incoming/Trade Analysis - ADA-USDT - Binance.png"
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
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(header=("Date(UTC)", "Pair", "Side", "Price", "Executed", "Amount", "Fee")),
    )

    assert route.category == "source_raw"
    assert route.capture_id == "2022-03"
    assert route.target_path == (
        workspace_root / "evidence/raw/source/binance/2022-03/202203291736/archive/202203291736.zip"
    )
