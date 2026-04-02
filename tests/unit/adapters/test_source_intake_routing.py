from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoutingRequest


def test_binance_adapter_matches_intake_from_header_hints() -> None:
    adapter = build_registry().source_adapter("binance")

    score = adapter.match_intake(
        "incoming/neutral/capture.csv",
        IntakeFileFacts(header=("Pair", "Coin", "Date", "Amount", "Type", "Status")),
    )

    assert score == 100


def test_cointracking_portfolio_adapter_routes_html_export(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    html_path = incoming_dir / "CoinTracking Export.html"
    html_path.write_text(
        "<html><body>Created by: CoinTracking as of: 06.04.2022 01:11</body></html>",
        encoding="utf-8",
    )
    workspace_root = tmp_path / "workspace"
    adapter = build_registry().source_adapter("cointracking_portfolio")

    route = adapter.route_intake(
        IntakeRoutingRequest(
            relative_path=html_path.name,
            file_path=html_path,
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            facts=IntakeFileFacts(),
        )
    )

    assert route is not None
    assert route.role == "portfolio_export"
    assert route.capture_id == "2022-04"
    assert route.target_path == (
        workspace_root / "evidence/raw/portfolio/cointracking/2022-04/CoinTracking Export.html"
    )
