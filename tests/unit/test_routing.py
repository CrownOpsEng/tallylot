from __future__ import annotations

from pathlib import Path

import routing


def test_resolve_routing_decision_routes_cointracking_exports_to_ledger_history(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming_root = repo_root / "01_raw_exports" / "incoming"
    path = incoming_root / "CoinTracking - 2021 Tax Export - Summary.pdf"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"%PDF-1.4\n")

    decision = routing.resolve_routing_decision(
        repo_root=repo_root,
        incoming_root=incoming_root,
        path=path,
        inspection_row={"family": "statement_balance_pdf", "min_timestamp": "", "max_timestamp": ""},
    )

    assert decision.role == "ledger_export"
    assert "01_raw_exports/cointracking/history" in str(decision.destination_dir)
    assert decision.bundle_type == "single_file_bundle"


def test_resolve_routing_decision_defaults_binance_loose_files_to_source_raw(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming_root = repo_root / "01_raw_exports" / "incoming"
    path = incoming_root / "borrow.csv"
    path.parent.mkdir(parents=True)
    path.write_text(
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n",
        encoding="utf-8",
    )

    decision = routing.resolve_routing_decision(
        repo_root=repo_root,
        incoming_root=incoming_root,
        path=path,
        inspection_row={"family": "binance_margin_borrow_csv", "min_timestamp": "2021-05-25 12:53:03", "max_timestamp": "2021-05-25 12:53:03"},
    )

    assert decision.role == "source_raw"
    assert decision.source_folder == "binance"
    assert decision.capture_id == "2021-05"
    assert decision.bundle_type == "synthetic_companion_bundle"
    assert decision.bundle_id == "binance-isolated-margin-loose"
