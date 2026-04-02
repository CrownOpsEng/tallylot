from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.services.intake_file_facts import detect_capture_id, inspect_intake_file
from crypto_reconciliation.application.services.intake_routing import detect_source_folder


def test_inspect_intake_file_extracts_timestamps_scope_tokens_and_network_hints(tmp_path: Path) -> None:
    path = tmp_path / "bundle_20220329.csv"
    path.write_text(
        "Timestamp,Network,Address\n"
        "2022-03-29 18:30:00,Ethereum,0x1111111111111111111111111111111111111111\n"
        "2022-03-30 18:30:00,Ethereum,0x2222222222222222222222222222222222222222\n",
        encoding="utf-8",
    )

    facts = inspect_intake_file(path, relative_path="incoming/account-main/bundle_20220329.csv")

    assert facts.min_timestamp == "2022-03-29 18:30:00"
    assert facts.max_timestamp == "2022-03-30 18:30:00"
    assert "evm:0x1111111111111111111111111111111111111111" in facts.scope_tokens
    assert "label:account-main" in facts.scope_tokens
    assert "ethereum" in facts.network_hints
    assert detect_capture_id("incoming/account-main/bundle_20220329.csv", facts) == "2022-03"


def test_detect_source_folder_uses_header_hints_without_filename_tokens(tmp_path: Path) -> None:
    path = tmp_path / "capture.csv"
    path.write_text(
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n",
        encoding="utf-8",
    )

    facts = inspect_intake_file(path, relative_path="incoming/neutral/capture.csv")

    assert detect_source_folder("incoming/neutral/capture.csv", facts) == "binance"
