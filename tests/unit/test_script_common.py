from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

import script_common


def test_require_directory_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        script_common.require_directory(tmp_path / "missing", "Export directory")


def test_require_directory_rejects_file_path(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("x", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        script_common.require_directory(path, "Export directory")


def test_require_file_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        script_common.require_file(tmp_path / "missing.csv", "CSV")


def test_read_and_write_csv_rows_round_trip(tmp_path: Path) -> None:
    rows = [{"filename": "a.csv", "size_bytes": 1, "sha256": "abc"}]
    path = tmp_path / "manifest.csv"
    script_common.write_csv_rows(path, ["filename", "size_bytes", "sha256"], rows)

    assert script_common.read_csv_rows(path) == [{"filename": "a.csv", "size_bytes": "1", "sha256": "abc"}]


def test_read_csv_rows_accepts_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "manifest.csv"
    path.write_text("\ufefffilename,size_bytes,sha256\na.csv,1,abc\n", encoding="utf-8")

    assert script_common.read_csv_rows(path) == [{"filename": "a.csv", "size_bytes": "1", "sha256": "abc"}]


def test_write_csv_rows_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "manifest.csv"
    script_common.write_csv_rows(path, ["filename", "size_bytes", "sha256"], [{"filename": "a.csv", "size_bytes": 1, "sha256": "abc"}])

    assert path.exists()


def test_find_matching_csv_files_returns_sorted_csv_matches_only(tmp_path: Path) -> None:
    export_dir = tmp_path
    (export_dir / "b Trade Table.csv").write_text("", encoding="utf-8")
    (export_dir / "a Trade Table.csv").write_text("", encoding="utf-8")
    (export_dir / "Trade Table.txt").write_text("", encoding="utf-8")

    matches = script_common.find_matching_csv_files(export_dir, "Trade Table")

    assert [path.name for path in matches] == ["a Trade Table.csv", "b Trade Table.csv"]


def test_find_required_csv_exports_rejects_missing_required_export(tmp_path: Path) -> None:
    export_dir = tmp_path
    (export_dir / "Current Balance.csv").write_text("", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Trade Table"):
        script_common.find_required_csv_exports(
            export_dir,
            {"trade_table": "Trade Table", "current_balance": "Current Balance"},
            "Export directory",
        )


def test_find_required_csv_exports_rejects_ambiguous_match(tmp_path: Path) -> None:
    export_dir = tmp_path
    (export_dir / "a Trade Table.csv").write_text("", encoding="utf-8")
    (export_dir / "b Trade Table.csv").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Ambiguous export"):
        script_common.find_required_csv_exports(
            export_dir,
            {"trade_table": "Trade Table"},
            "Export directory",
        )


def test_find_required_csv_exports_returns_exact_mapping(tmp_path: Path) -> None:
    export_dir = tmp_path
    trade = export_dir / "Trade Table.csv"
    balance = export_dir / "Current Balance.csv"
    trade.write_text("", encoding="utf-8")
    balance.write_text("", encoding="utf-8")

    files = script_common.find_required_csv_exports(
        export_dir,
        {"trade_table": "Trade Table", "current_balance": "Current Balance"},
        "Export directory",
    )

    assert files["trade_table"] == trade.resolve()
    assert files["current_balance"] == balance.resolve()


def test_decimal_text_quantizes_to_eight_places() -> None:
    assert script_common.decimal_text(Decimal("1.234567891")) == "1.23456789"
    assert script_common.decimal_text(Decimal("-0.00000001")) == "-0.00000001"


def test_parse_decimal_handles_currency_text_and_parentheses() -> None:
    assert script_common.parse_decimal("$1,234.56") == Decimal("1234.56")
    assert script_common.parse_decimal("(4.50)") == Decimal("-4.50")
    assert script_common.parse_decimal("") is None


def test_decimal_or_zero_returns_zero_for_blank_values() -> None:
    assert script_common.decimal_or_zero("") == Decimal("0")
    assert script_common.decimal_or_zero("1.23") == Decimal("1.23")


def test_parse_datetime_uses_first_matching_format() -> None:
    assert script_common.parse_datetime("2026-03-24 10:11:12", ("%Y-%m-%d %H:%M:%S",)) == datetime(2026, 3, 24, 10, 11, 12)


def test_parse_datetime_to_utc_naive_handles_literal_utc_and_offsets() -> None:
    literal_utc = script_common.parse_datetime_to_utc_naive(
        "2026-03-24 10:11:12 UTC",
        ("%Y-%m-%d %H:%M:%S UTC",),
    )
    offset_value = script_common.parse_datetime_to_utc_naive(
        "2026-03-24 10:11:12-0600",
        ("%Y-%m-%d %H:%M:%S%z",),
    )

    assert literal_utc == datetime(2026, 3, 24, 10, 11, 12)
    assert offset_value == datetime(2026, 3, 24, 16, 11, 12)


def test_parse_datetime_to_utc_naive_applies_source_timezone_when_needed() -> None:
    parsed = script_common.parse_datetime_to_utc_naive(
        "2026-03-24 10:11:12",
        ("%Y-%m-%d %H:%M:%S",),
        source_timezone=timezone.utc,
    )

    assert parsed == datetime(2026, 3, 24, 10, 11, 12)


def test_parse_utc_offset_label_supports_binance_style_negative_offsets() -> None:
    negative = script_common.parse_utc_offset_label("--6")
    zero = script_common.parse_utc_offset_label("0")
    half_hour = script_common.parse_utc_offset_label("+05:30")

    assert datetime.now(negative).strftime("%z") == "-0600"
    assert datetime.now(zero).strftime("%z") == "+0000"
    assert datetime.now(half_hour).strftime("%z") == "+0530"


def test_source_timezone_from_filename_reads_embedded_utc_offset() -> None:
    parsed = script_common.source_timezone_from_filename("Binance-Spot-Trade-History-202603230406(UTC--6)_5d63c10c.csv")

    assert parsed is not None
    assert datetime.now(parsed).strftime("%z") == "-0600"


def test_normalize_whitespace_collapses_runs() -> None:
    assert script_common.normalize_whitespace(" a \n b\tc ") == "a b c"


def test_read_and_write_cointracking_rows_round_trip(tmp_path: Path) -> None:
    rows = [
        {
            "Type": "Trade",
            "Buy": "1.00000000",
            "Buy Cur.": "BTC",
            "Sell": "10.00000000",
            "Sell Cur.": "CAD",
            "Fee": "0.10000000",
            "Fee Cur.": "CAD",
            "Exchange": "Coinbase",
            "Group": "",
            "Comment": "Test row",
            "Date": "2026-03-24 10:11:12",
            "Tx-ID": "tx-1",
            "match_window_seconds": "2",
        }
    ]
    path = tmp_path / "cointracking.csv"
    script_common.write_cointracking_rows(path, rows, extra_headers=("match_window_seconds",))

    assert script_common.read_cointracking_rows(path, extra_headers=("match_window_seconds",)) == rows


def test_read_cointracking_rows_accepts_trade_table_header_with_lpn(tmp_path: Path) -> None:
    path = tmp_path / "trade_table.csv"
    path.write_text(
        (
            "Type,Buy,Cur.,Sell,Cur.,Fee,Cur.,Exchange,Group,Comment,Date,LPN,Tx-ID\n"
            "Trade,1.00000000,BTC,10.00000000,CAD,0.10000000,CAD,Coinbase,,Test row,2026-03-24 10:11:12,,tx-1\n"
        ),
        encoding="utf-8",
    )

    read_back = script_common.read_cointracking_rows(path)

    assert read_back[0]["Tx-ID"] == "tx-1"
    assert read_back[0]["Buy Cur."] == "BTC"


def test_write_json_creates_parent_directories_and_sorts_keys(tmp_path: Path) -> None:
    payload = {"b": 2, "a": 1}
    path = tmp_path / "nested" / "summary.json"
    script_common.write_json(path, payload)

    text = path.read_text(encoding="utf-8")
    parsed = json.loads(text)

    assert text.endswith("\n")
    assert text.find('"a"') < text.find('"b"')
    assert parsed == payload


def test_default_verification_exports_are_in_expected_order() -> None:
    assert list(script_common.DEFAULT_VERIFICATION_EXPORTS) == [
        "Validate Transactions",
        "Missing Transactions",
        "Duplicate Transactions",
        "Current Balance",
        "Balance by Exchange",
    ]
