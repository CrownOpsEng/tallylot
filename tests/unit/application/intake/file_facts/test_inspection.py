from __future__ import annotations

from pathlib import Path

from tallylot.application.intake.file_facts import (
    IntakeFileFacts,
    detect_capture_label,
    inspect_intake_file,
)
from tallylot.application.intake.file_facts.inspection import parse_timestamp
from tallylot.application.intake.routing.service import _detect_source_folder
from tallylot.infrastructure.discovery import build_registry


def test_inspect_intake_file_extracts_timestamps_scope_tokens_and_network_hints(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bundle_20220329.csv"
    path.write_text(
        "Timestamp,Network,Address\n"
        "2022-03-29 18:30:00,Ethereum,0x1111111111111111111111111111111111111111\n"
        "2022-03-30 18:30:00,Ethereum,0x2222222222222222222222222222222222222222\n",
        encoding="utf-8",
    )

    facts = inspect_intake_file(
        path, relative_path="incoming/account-main/bundle_20220329.csv"
    )

    assert facts.min_timestamp == "2022-03-29 18:30:00"
    assert facts.max_timestamp == "2022-03-30 18:30:00"
    assert "evm:0x1111111111111111111111111111111111111111" in facts.scope_tokens
    assert "label:account-main" in facts.scope_tokens
    assert "ethereum" in facts.network_hints
    assert (
        detect_capture_label("incoming/account-main/bundle_20220329.csv", facts)
        == "2022-03"
    )


def test_detect_source_folder_uses_header_hints_without_filename_tokens(
    tmp_path: Path,
) -> None:
    path = tmp_path / "capture.csv"
    path.write_text(
        "Pair,Coin,Date,Amount,Type,Status\nADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n",
        encoding="utf-8",
    )

    facts = inspect_intake_file(path, relative_path="incoming/neutral/capture.csv")

    assert (
        _detect_source_folder(build_registry(), "incoming/neutral/capture.csv", facts)
        == "binance"
    )


def test_inspect_intake_file_skips_title_rows_before_coinbase_headers(
    tmp_path: Path,
) -> None:
    path = tmp_path / "retail-export.csv"
    path.write_text(
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,"
        "Price at Transaction,Subtotal,Total (inclusive of fees and/or spread),"
        "Fees and/or Spread,Notes\n"
        "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,"
        "$610.00,$10.00,Bought 0.01 BTC for 610 CAD\n",
        encoding="utf-8",
    )

    facts = inspect_intake_file(
        path, relative_path="incoming/neutral/retail-export.csv"
    )

    assert facts.header == (
        "ID",
        "Timestamp",
        "Transaction Type",
        "Asset",
        "Quantity Transacted",
        "Price Currency",
        "Price at Transaction",
        "Subtotal",
        "Total (inclusive of fees and/or spread)",
        "Fees and/or Spread",
        "Notes",
    )
    assert facts.min_timestamp == "2024-02-08 16:31:22"
    assert facts.max_timestamp == "2024-02-08 16:31:22"


def test_inspect_intake_file_supports_semicolon_delimited_headers(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bot-1-deals.csv"
    path.write_text(
        "deal_id;status;bot;account;bot_id;pair\n1;completed;ADA Bot;acct;9;USDT_ADA\n",
        encoding="utf-8",
    )

    facts = inspect_intake_file(path, relative_path="incoming/neutral/bot-1-deals.csv")

    assert facts.header == ("deal_id", "status", "bot", "account", "bot_id", "pair")


def test_detect_capture_label_prefers_end_of_filename_date_range() -> None:
    assert (
        detect_capture_label(
            "incoming/Coinbase/Coinbase Pro Trades 2018.01.01 - 2021.08.14.csv",
            IntakeFileFacts(),
        )
        == "2021-08"
    )


def test_detect_capture_label_uses_standalone_year_when_month_is_absent() -> None:
    assert (
        detect_capture_label(
            "incoming/2021/Kucoin/KuCoin USDT 624ce53ee5546b00017ad02e_balance2686417537154910221.zip",
            IntakeFileFacts(),
        )
        == "2021"
    )


def test_detect_capture_label_parses_month_day_year_filenames() -> None:
    assert (
        detect_capture_label(
            "incoming/Coinberry Activity Report - 08-14-2021 v1.csv",
            IntakeFileFacts(),
        )
        == "2021-08"
    )


def test_detect_capture_label_parses_compact_archive_timestamps() -> None:
    assert (
        detect_capture_label("incoming/202201152304.zip", IntakeFileFacts())
        == "2022-01"
    )


def test_detect_capture_label_prefers_content_timestamp_when_available() -> None:
    assert (
        detect_capture_label(
            "incoming/Coinbase TransactionsHistoryReport-2021-11-03-11_26_30.csv",
            IntakeFileFacts(min_timestamp="2021-10-30 00:00:00"),
        )
        == "2021-10"
    )


def test_inspect_intake_file_extracts_non_evm_scope_tokens_from_content(
    tmp_path: Path,
) -> None:
    path = tmp_path / "wallets.csv"
    path.write_text(
        "Address,Public Key\n"
        "bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,"
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
        encoding="utf-8",
    )

    facts = inspect_intake_file(path, relative_path="incoming/Account 1/wallets.csv")

    assert "btc:bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in facts.scope_tokens
    assert (
        "cardano:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        in facts.scope_tokens
    )


def test_inspect_intake_file_extracts_tron_scope_tokens_from_content(
    tmp_path: Path,
) -> None:
    path = tmp_path / "wallets.csv"
    path.write_text(
        "Address,Date(UTC)\nTAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,2022-03-28 13:01:36\n",
        encoding="utf-8",
    )

    facts = inspect_intake_file(path, relative_path="incoming/neutral/wallets.csv")

    assert "tron:TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" in facts.scope_tokens


def test_detect_source_folder_uses_filename_hints_without_header_match() -> None:
    assert (
        _detect_source_folder(
            build_registry(),
            "incoming/Wealthsimple/statement-export.csv",
            IntakeFileFacts(),
        )
        == "wealthsimple"
    )


def test_parse_timestamp_accepts_fractional_second_utc_values() -> None:
    parsed = parse_timestamp("2021-05-10T02:37:18.689Z")

    assert parsed is not None
    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == "2021-05-10 02:37:18"
