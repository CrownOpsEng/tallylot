from __future__ import annotations

from pathlib import Path

import inspection


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
