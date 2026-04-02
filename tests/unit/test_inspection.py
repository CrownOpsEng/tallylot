from __future__ import annotations

from pathlib import Path
import zipfile

import inspection
import pytest
from tests.support.helpers import write_minimal_xlsx


def test_detect_csv_header_supports_semicolon_delimited_rows(tmp_path: Path) -> None:
    path = tmp_path / "bot-1-deals.csv"
    path.write_text(
        "deal_id;status;bot;account;bot_id;pair\n"
        "1;completed;ADA Bot;acct;9;USDT_ADA\n",
        encoding="utf-8",
    )

    header, index = inspection.detect_csv_header(path)

    assert index == 0
    assert header == ["deal_id", "status", "bot", "account", "bot_id", "pair"]
    assert inspection.classify_file_family(path, header) == "trading_bot_deals_csv"


def test_infer_historical_date_prefers_filename_month(tmp_path: Path) -> None:
    path = tmp_path / "Coinbase TransactionsHistoryReport-2021-11-03-11_26_30.csv"
    path.write_text("Timestamp,Transaction Type\n", encoding="utf-8")

    decision = inspection.infer_historical_date((path.name,), inspection.inspect_file(path))

    assert decision.capture_id == "2021-11"
    assert decision.review_required is False


def test_infer_historical_date_prefers_end_of_range() -> None:
    decision = inspection.infer_historical_date(("Coinbase Pro Trades 2018.01.01 - 2021.08.14.csv",), {"family": "fills_csv"})

    assert decision.capture_id == "2021-08"
    assert decision.basis == "filename_or_folder:2021.08.14"


def test_infer_historical_date_falls_back_to_content_span(tmp_path: Path) -> None:
    path = tmp_path / "borrow.csv"
    path.write_text(
        "Pair,Coin,Date,Amount,Type,Status\n"
        "ADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n",
        encoding="utf-8",
    )

    decision = inspection.infer_historical_date((path.name,), inspection.inspect_file(path))

    assert decision.capture_id == "2021-05"
    assert decision.basis.startswith("content_span:")


def test_infer_historical_date_ignores_long_numeric_ids(tmp_path: Path) -> None:
    path = tmp_path / "KuCoin USDT 624ce53ee5546b00017ad02e_balance2686417537154910221.zip"
    path.write_text("", encoding="utf-8")

    decision = inspection.infer_historical_date((path.name, "2021", "Kucoin"), inspection.inspect_file(path))

    assert decision.capture_id == "2021"
    assert decision.basis == "filename_or_folder:2021"


def test_infer_historical_date_parses_compact_archive_timestamps() -> None:
    decision = inspection.infer_historical_date(("202201152304.zip",), {"family": "archive_bundle"})

    assert decision.capture_id == "2022-01"


def test_infer_historical_date_parses_unambiguous_month_day_year_filename_dates() -> None:
    decision = inspection.infer_historical_date(("Coinberry Activity Report - 08-14-2021 v1.csv",), {"family": "coinberry_activity_csv"})

    assert decision.capture_id == "2021-08"
    assert decision.basis == "filename_or_folder:08-14-2021"


def test_infer_historical_date_can_disable_content_span(tmp_path: Path) -> None:
    path = tmp_path / "CoinTracking · Trade Table.csv"
    path.write_text(
        "Type,Buy,Cur.,Sell,Cur.,Fee,Cur.,Exchange,Date\n"
        "Trade,1,BTC,10,CAD,0.1,CAD,CoinTracking,2019-09-10 19:01:50\n",
        encoding="utf-8",
    )

    decision = inspection.infer_historical_date(
        (path.name,),
        inspection.inspect_file(path),
        policy=inspection.HistoricalDatePolicy(allow_content_span=False),
    )

    assert decision.review_required is True


def test_inspect_file_identifies_crypto_archive_contents(tmp_path: Path) -> None:
    archive = tmp_path / "202203291736.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(
            "part-00000.csv",
            (
                "Date(UTC),Pair,Side,Price,Executed,Amount,Fee\n"
                "2022-03-28 13:01:36,SOLBUSD,SELL,110.03,0.1800000000SOL,19.8054BUSD,0.0198054BUSD\n"
            ),
        )

    row = inspection.inspect_file(archive)

    assert row["family"] == "binance_margin_trade_csv"
    assert row["archive_detected_source"] == "Binance"
    assert row["archive_contains_crypto_records"] == "yes"


def test_inspect_file_prefers_content_scope_tokens_over_filename_labels(tmp_path: Path) -> None:
    path = tmp_path / "account-main-report.csv"
    path.write_text(
        "Address,Date(UTC),Pair,Side,Price,Executed,Amount,Fee\n"
        "0x1111111111111111111111111111111111111111,2022-03-28 13:01:36,SOLBUSD,SELL,110.03,0.1800000000SOL,19.8054BUSD,0.0198054BUSD\n",
        encoding="utf-8",
    )

    row = inspection.inspect_file(path)

    assert row["content_scope_tokens"] == "evm:0x1111111111111111111111111111111111111111"
    assert row["path_scope_tokens"] == "account:main"
    assert row["scope_tokens"] == "evm:0x1111111111111111111111111111111111111111"


def test_inspect_file_extracts_explorer_scope_from_single_owned_to_column(tmp_path: Path) -> None:
    path = tmp_path / "explorer-export.csv"
    path.write_text(
        "Transaction Hash,Blockno,UnixTimestamp,DateTime (UTC),TokenValue,TokenSymbol,From,To\n"
        "0xabc,1,1710000000,2024-03-09 09:41:37,1,GALA,0x0,0x2222222222222222222222222222222222222222\n",
        encoding="utf-8",
    )

    row = inspection.inspect_file(path)

    assert row["content_scope_tokens"] == "evm:0x2222222222222222222222222222222222222222"


@pytest.mark.parametrize(
    ("header", "value", "expected_token"),
    [
        ("Address", "bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "btc:bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
        ("Address", "TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "tron:TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"),
        ("Public Key", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "cardano:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
    ],
)
def test_inspect_file_extracts_non_evm_wallet_scope_tokens_from_content(tmp_path: Path, header: str, value: str, expected_token: str) -> None:
    path = tmp_path / "wallet.csv"
    path.write_text(
        f"{header},Date(UTC),Pair,Side,Price,Executed,Amount,Fee\n"
        f"{value},2022-03-28 13:01:36,SOLBUSD,SELL,110.03,0.1800000000SOL,19.8054BUSD,0.0198054BUSD\n",
        encoding="utf-8",
    )

    row = inspection.inspect_file(path)

    assert row["content_scope_tokens"] == expected_token


def test_inspect_file_classifies_binance_staking_workbook_and_export_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "Staking History-2022-03-22_2022-04-05.xlsx"
    write_minimal_xlsx(
        path,
        rows=[
            ["Redemption Date(UTC)", "Coin", "Redemption Amount", "Status"],
            ["2022-04-05 21:00:00", "ADA", "5.00000000", "Completed"],
        ],
        modified_at="2022-04-05T21:34:36Z",
    )

    row = inspection.inspect_file(path)

    assert row["family"] == "binance_staking_redemption_csv"
    assert row["date_field"] == "Redemption Date(UTC)"
    assert row["min_timestamp"] == "2022-04-05 21:00:00"
    assert row["export_timestamp"] == "2022-04-05 21:34:36"
    assert row["workbook_sheet_names"] == "Sheet1"


def test_inspect_file_extracts_cointracking_html_export_timestamp_and_period(tmp_path: Path) -> None:
    path = tmp_path / "CoinTracking · Tax Declaration Export.html"
    path.write_text(
        """
        <html>
        <head><title>CoinTracking · Tax Declaration Export</title></head>
        <body>
        Created by: CoinTracking as of: 06.04.2022 01:11
        <p>period from <strong>01.01.2021</strong> until <strong>31.12.2021</strong></p>
        </body>
        </html>
        """,
        encoding="utf-8",
    )

    row = inspection.inspect_file(path)

    assert row["family"] == "cointracking_tax_declaration_html"
    assert row["export_timestamp"] == "2022-04-06 01:11:00"
    assert row["report_period_start"] == "2021-01-01 00:00:00"
    assert row["report_period_end"] == "2021-12-31 00:00:00"


@pytest.mark.parametrize(
    ("filename", "payload", "expected_family"),
    [
        (
            "Coinberry Transaction History.csv",
            "Receipt No,Date,Activity,Amount,Currency,CAD Amount,CAD Rate\n1,2022-01-01,Buy,1.0,BTC,100.00,100.00\n",
            "coinberry_activity_csv",
        ),
        (
            "transactions_summary.csv",
            (
                "Transaction Type,Date,Amount Debited,Debit Currency,Amount Credited,Credit Currency,"
                "Buy / Sell Rate,Direction,Spot Rate,Source / Destination\n"
                "Buy,2022-01-01 10:00:00,100.00,CAD,0.00100000,BTC,100000.00,In,100000.00,Shakepay\n"
            ),
            "shakepay_transactions_csv",
        ),
    ],
)
def test_inspect_file_classifies_common_csv_export_families(tmp_path: Path, filename: str, payload: str, expected_family: str) -> None:
    path = tmp_path / filename
    path.write_text(payload, encoding="utf-8")

    row = inspection.inspect_file(path)

    assert row["family"] == expected_family


def test_inspect_file_classifies_gemini_account_history_workbook(tmp_path: Path) -> None:
    path = tmp_path / "History.xlsx"
    write_minimal_xlsx(
        path,
        rows=[
            ["Date", "Time (UTC)", "Type", "Symbol", "Specification"],
            ["2022-01-01", "10:00:00", "Credit", "BTC", "Deposit"],
        ],
        modified_at="2022-01-02T01:02:03Z",
    )

    row = inspection.inspect_file(path)

    assert row["family"] == "gemini_account_history_csv"
    assert row["export_timestamp"] == "2022-01-02 01:02:03"


def test_inspect_file_marks_mixed_portfolio_workbook_as_artifact(tmp_path: Path) -> None:
    path = tmp_path / "WealthSimple Trade + Crypto.xlsx"
    write_minimal_xlsx(
        path,
        rows=[
            ["Date", "Type", "Buy Amount", "Buy Cur.", "Sell Amount", "Sell Cur."],
            ["2022-01-01", "Trade", "1.00000000", "BTC", "100.00", "CAD"],
            ["Wealthsimple Trade (Non-Registered - WS Crypto)", "", "", "", "", ""],
            ["Wealthsimple Crypto (Crypto)", "", "", "", "", ""],
        ],
        modified_at="2022-01-03T04:05:06Z",
    )

    row = inspection.inspect_file(path)

    assert row["family"] == "mixed_portfolio_workbook"
    assert row["artifact_kind"] == "mixed_portfolio_workbook"
    assert row["artifact_reason"] == "User-assembled mixed workbook artifact."
