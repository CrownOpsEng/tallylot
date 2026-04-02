from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.services.intake.file_facts import (
    IntakeFileFacts,
    detect_capture_id,
    inspect_intake_file,
)
from crypto_reconciliation.application.services.intake.routing import detect_source_folder


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


def test_inspect_intake_file_supports_semicolon_delimited_headers(tmp_path: Path) -> None:
    path = tmp_path / "bot-1-deals.csv"
    path.write_text(
        "deal_id;status;bot;account;bot_id;pair\n1;completed;ADA Bot;acct;9;USDT_ADA\n",
        encoding="utf-8",
    )

    facts = inspect_intake_file(path, relative_path="incoming/neutral/bot-1-deals.csv")

    assert facts.header == ("deal_id", "status", "bot", "account", "bot_id", "pair")


def test_detect_capture_id_prefers_end_of_filename_date_range() -> None:
    assert (
        detect_capture_id(
            "incoming/Coinbase/Coinbase Pro Trades 2018.01.01 - 2021.08.14.csv",
            IntakeFileFacts(),
        )
        == "2021-08"
    )


def test_detect_capture_id_uses_standalone_year_when_month_is_absent() -> None:
    assert (
        detect_capture_id(
            "incoming/2021/Kucoin/KuCoin USDT 624ce53ee5546b00017ad02e_balance2686417537154910221.zip",
            IntakeFileFacts(),
        )
        == "2021"
    )


def test_detect_capture_id_parses_month_day_year_filenames() -> None:
    assert (
        detect_capture_id(
            "incoming/Coinberry Activity Report - 08-14-2021 v1.csv",
            IntakeFileFacts(),
        )
        == "2021-08"
    )


def test_detect_capture_id_parses_compact_archive_timestamps() -> None:
    assert detect_capture_id("incoming/202201152304.zip", IntakeFileFacts()) == "2022-01"


def test_detect_capture_id_prefers_content_timestamp_when_available() -> None:
    assert (
        detect_capture_id(
            "incoming/Coinbase TransactionsHistoryReport-2021-11-03-11_26_30.csv",
            IntakeFileFacts(min_timestamp="2021-10-30 00:00:00"),
        )
        == "2021-10"
    )


def test_inspect_intake_file_extracts_non_evm_scope_tokens_from_content(tmp_path: Path) -> None:
    path = tmp_path / "wallets.csv"
    path.write_text(
        "Address,Public Key\n"
        "bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,"
        "5ebb4c94284e7c805f247a6c7fbbb705bf3c1a234889401321c351aa05d468b6"
        "ddb9577f143d435ea4bba178a611110f309c930e5400ac960b4bed9e912f2825\n",
        encoding="utf-8",
    )

    facts = inspect_intake_file(path, relative_path="incoming/Account 1/wallets.csv")

    assert "btc:bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in facts.scope_tokens
    assert (
        "cardano:5ebb4c94284e7c805f247a6c7fbbb705bf3c1a234889401321c351aa05d468b6"
        "ddb9577f143d435ea4bba178a611110f309c930e5400ac960b4bed9e912f2825" in facts.scope_tokens
    )


def test_inspect_intake_file_extracts_tron_scope_tokens_from_content(tmp_path: Path) -> None:
    path = tmp_path / "wallets.csv"
    path.write_text(
        "Address,Date(UTC)\nTAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,2022-03-28 13:01:36\n",
        encoding="utf-8",
    )

    facts = inspect_intake_file(path, relative_path="incoming/neutral/wallets.csv")

    assert "tron:TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" in facts.scope_tokens


def test_detect_source_folder_uses_filename_hints_without_header_match() -> None:
    assert (
        detect_source_folder(
            "incoming/Wealthsimple/statement-export.csv",
            IntakeFileFacts(),
        )
        == "wealthsimple"
    )
