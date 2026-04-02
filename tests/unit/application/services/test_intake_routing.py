from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.services.archive_scan import ScannedFile
from crypto_reconciliation.application.services.intake_file_facts import IntakeFileFacts
from crypto_reconciliation.application.services.intake_routing import route_intake_file


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
