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


def test_resolve_routing_decision_uses_inventory_backed_wallet_source_from_content_scope(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming_root = repo_root / "01_raw_exports" / "incoming"
    path = incoming_root / "Account1-bsc export-address-token.csv"
    path.parent.mkdir(parents=True)
    path.write_text(
        "Transaction Hash,Blockno,UnixTimestamp,DateTime (UTC),TokenValue,TokenSymbol,From,To\n"
        "0xabc,1,1710000000,2024-03-09 09:41:37,1,GALA,0x0,0x2222222222222222222222222222222222222222\n",
        encoding="utf-8",
    )
    source_inventory = repo_root / "03_analysis" / "issues" / "source_inventory.csv"
    source_inventory.parent.mkdir(parents=True, exist_ok=True)
    source_inventory.write_text(
        "source,activity_after_cutoff,first_post_cutoff_tx,export_window_start,export_window_end,import_order,status,capture_path,profile_status,adapter,normalization_status,exception_count,candidate_path,notes\n"
        "eth-gala1,yes,,2023-08-05 08:34:05,2025-12-31 23:59:59,1,capture_complete,01_raw_exports/external/eth-gala1/2026-03,profiled,evm_explorer,ready,0,,\n",
        encoding="utf-8",
    )
    wallet_evidence = repo_root / "03_analysis" / "inventory" / "wallet_inventory_evidence.csv"
    wallet_evidence.parent.mkdir(parents=True, exist_ok=True)
    wallet_evidence.write_text(
        "source,raw_dir,wallet_id,identifier_kind,normalized_identifier,display_identifier,network_scope,controller,account_label,evidence_kind,evidence_path,confidence,note\n"
        "eth-gala1,/tmp/capture,evm_address:0x2222222222222222222222222222222222222222,evm_address,0x2222222222222222222222222222222222222222,0x2222222222222222222222222222222222222222,ethereum,Explorer export,Account 2,filename,/tmp/evidence.csv,high,\n",
        encoding="utf-8",
    )

    decision = routing.resolve_routing_decision(
        repo_root=repo_root,
        incoming_root=incoming_root,
        path=path,
        inspection_row={
            "family": "explorer_token_transfer_csv",
            "header_preview": "Transaction Hash | Blockno | UnixTimestamp | DateTime (UTC) | TokenValue | TokenSymbol | From | To",
            "scope_tokens": "evm:0x2222222222222222222222222222222222222222",
            "min_timestamp": "2024-03-09 09:41:37",
            "max_timestamp": "2024-03-09 09:41:37",
        },
    )

    assert decision.source_label == "eth-gala1"
    assert decision.source_folder == "eth-gala1"
    assert decision.inventory_match_status == "inventory_source_match"
    assert decision.review_required is False


def test_resolve_routing_decision_keeps_generic_wallet_when_inventory_match_is_ambiguous(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming_root = repo_root / "01_raw_exports" / "incoming"
    path = incoming_root / "account-export.csv"
    path.parent.mkdir(parents=True)
    path.write_text(
        "Transaction Hash,Blockno,UnixTimestamp,DateTime (UTC),TokenValue,TokenSymbol,From,To\n"
        "0xabc,1,1710000000,2024-03-09 09:41:37,1,GALA,0x0,0x1111111111111111111111111111111111111111\n",
        encoding="utf-8",
    )
    source_inventory = repo_root / "03_analysis" / "issues" / "source_inventory.csv"
    source_inventory.parent.mkdir(parents=True, exist_ok=True)
    source_inventory.write_text(
        "source,activity_after_cutoff,first_post_cutoff_tx,export_window_start,export_window_end,import_order,status,capture_path,profile_status,adapter,normalization_status,exception_count,candidate_path,notes\n"
        "eth-metamask1,yes,,2023-08-05 08:34:05,2025-12-31 23:59:59,1,capture_complete,01_raw_exports/external/eth-metamask1/2026-03,profiled,evm_explorer,ready,0,,\n"
        "polygon-metamask1,yes,,2023-08-05 08:34:05,2025-12-31 23:59:59,2,capture_complete,01_raw_exports/external/polygon-metamask1/2026-03,profiled,evm_explorer,ready,0,,\n",
        encoding="utf-8",
    )
    wallet_evidence = repo_root / "03_analysis" / "inventory" / "wallet_inventory_evidence.csv"
    wallet_evidence.parent.mkdir(parents=True, exist_ok=True)
    wallet_evidence.write_text(
        "source,raw_dir,wallet_id,identifier_kind,normalized_identifier,display_identifier,network_scope,controller,account_label,evidence_kind,evidence_path,confidence,note\n"
        "eth-metamask1,/tmp/capture,evm_address:0x1111111111111111111111111111111111111111,evm_address,0x1111111111111111111111111111111111111111,0x1111111111111111111111111111111111111111,ethereum,Explorer export,Account 1,filename,/tmp/eth.csv,high,\n"
        "polygon-metamask1,/tmp/capture,evm_address:0x1111111111111111111111111111111111111111,evm_address,0x1111111111111111111111111111111111111111,0x1111111111111111111111111111111111111111,polygon,Explorer export,Account 1,filename,/tmp/poly.csv,high,\n",
        encoding="utf-8",
    )

    decision = routing.resolve_routing_decision(
        repo_root=repo_root,
        incoming_root=incoming_root,
        path=path,
        inspection_row={
            "family": "explorer_token_transfer_csv",
            "header_preview": "Transaction Hash | Blockno | UnixTimestamp | DateTime (UTC) | TokenValue | TokenSymbol | From | To",
            "scope_tokens": "evm:0x1111111111111111111111111111111111111111",
            "min_timestamp": "2024-03-09 09:41:37",
            "max_timestamp": "2024-03-09 09:41:37",
        },
    )

    assert decision.source_folder == "wallet-export-unassigned"
    assert decision.inventory_match_status == "inventory_source_ambiguous"
    assert decision.review_required is True
    assert "eth-metamask1" in decision.review_reason
    assert "polygon-metamask1" in decision.review_reason


def test_resolve_routing_decision_uses_generic_scope_folder_when_wallet_is_unknown(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    incoming_root = repo_root / "01_raw_exports" / "incoming"
    path = incoming_root / "Account 1" / "Account1-polygon export.csv"
    path.parent.mkdir(parents=True)
    path.write_text(
        "Transaction Hash,Blockno,UnixTimestamp,DateTime (UTC),TokenValue,TokenSymbol,From,To\n"
        "0xabc,1,1710000000,2024-03-09 09:41:37,1,GALA,0x0,0x1234567890abcdef1234567890abcdef12345678\n",
        encoding="utf-8",
    )

    decision = routing.resolve_routing_decision(
        repo_root=repo_root,
        incoming_root=incoming_root,
        path=path,
        inspection_row={
            "family": "explorer_token_transfer_csv",
            "header_preview": "Transaction Hash | Blockno | UnixTimestamp | DateTime (UTC) | TokenValue | TokenSymbol | From | To",
            "scope_tokens": "evm:0x1234567890abcdef1234567890abcdef12345678",
            "min_timestamp": "2024-03-09 09:41:37",
            "max_timestamp": "2024-03-09 09:41:37",
        },
    )

    assert decision.source_label == "Polygon Wallet 0x12345678"
    assert decision.source_folder == "polygon-wallet-0x12345678"
    assert decision.inventory_match_status == "generic_scope_routing"
    assert decision.review_required is False
