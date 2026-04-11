from __future__ import annotations

from pathlib import Path

from tallylot.application.intake import ScannedFile
from tallylot.application.intake.file_facts import IntakeFileFacts
from tallylot.application.intake.routing import route_intake_file
from tallylot.infrastructure.discovery import build_registry


def test_route_intake_file_routes_cointracking_pdf_to_portfolio_capture(
    tmp_path: Path,
) -> None:
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
        registry=build_registry(),
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(),
    )

    assert route.category == "portfolio_raw"
    assert route.role == "portfolio_export"
    assert route.capture_label == "2021"
    assert route.target_path == (
        workspace_root
        / "evidence/raw/portfolio/cointracking/2021/CoinTracking - 2021 Tax Export - Summary.pdf"
    )


def test_route_intake_file_routes_cointracking_sidecar_by_html_export_timestamp(
    tmp_path: Path,
) -> None:
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
        registry=build_registry(),
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(),
    )

    assert route.category == "portfolio_raw"
    assert route.role == "portfolio_sidecar"
    assert route.capture_label == "2022-04"
    assert route.target_path == (
        workspace_root
        / "evidence/raw/portfolio/cointracking/2022-04/CoinTracking Export_files/style.min.css"
    )


def test_route_intake_file_routes_cointracking_sidecar_to_unknown_capture_without_html(
    tmp_path: Path,
) -> None:
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
        registry=build_registry(),
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(),
    )

    assert route.category == "portfolio_raw"
    assert route.capture_label == "unknown"


def test_route_intake_file_routes_archive_sidecar_by_archive_capture_label(
    tmp_path: Path,
) -> None:
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
        registry=build_registry(),
        incoming_dir=incoming_dir,
        workspace_root=workspace_root,
        facts=IntakeFileFacts(),
    )

    assert route.category == "portfolio_raw"
    assert route.role == "portfolio_sidecar"
    assert route.capture_label == "2022-03"
