from __future__ import annotations

import json
from pathlib import Path

import pytest

import pipeline_common


def test_manifest_fingerprint_is_order_independent() -> None:
    rows_a = [
        {"filename": "b.csv", "size_bytes": "2", "sha256": "bbb"},
        {"filename": "a.csv", "size_bytes": "1", "sha256": "aaa"},
    ]
    rows_b = list(reversed(rows_a))

    assert pipeline_common.manifest_fingerprint_from_rows(rows_a) == pipeline_common.manifest_fingerprint_from_rows(rows_b)


def test_find_manifest_for_raw_dir_supports_capture_local_manifest(tmp_path: Path) -> None:
    raw_dir = tmp_path / "bsc-metamask1" / "2026-03"
    raw_dir.mkdir(parents=True)
    capture_manifest = raw_dir / "manifest.csv"
    capture_manifest.write_text("filename,size_bytes,sha256\n", encoding="utf-8")

    found = pipeline_common.find_manifest_for_raw_dir(raw_dir)

    assert found == capture_manifest


def test_build_file_inventory_classifies_known_csv_families(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "2026-03-23 Statement - All Time - account.csv").write_text(
        "Transactions\nID,Timestamp,Transaction Type\n",
        encoding="utf-8",
    )
    (raw_dir / "ledgerlive-operations.csv").write_text(
        "Operation Date,Status,Currency Ticker,Operation Type,Operation Amount\n",
        encoding="utf-8",
    )
    (raw_dir / "shakepay_Performance report_2025.pdf").write_bytes(b"%PDF-1.4\n")

    inventory = pipeline_common.build_file_inventory(raw_dir)

    by_name = {row["filename"]: row for row in inventory}
    assert by_name["2026-03-23 Statement - All Time - account.csv"]["family"] == "custodial_all_time_csv"
    assert by_name["ledgerlive-operations.csv"]["family"] == "wallet_operation_csv"
    assert by_name["shakepay_Performance report_2025.pdf"]["family"] == "statement_balance_pdf"


def test_build_file_inventory_classifies_metamask_state_json_without_filename_dependency(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "wallet-state-backup.json").write_text(
        json.dumps({"metamask": {"identities": {}}}),
        encoding="utf-8",
    )

    inventory = pipeline_common.build_file_inventory(raw_dir)

    assert inventory == [
        {
            "filename": "wallet-state-backup.json",
            "suffix": ".json",
            "family": "metamask_state_json",
            "header_preview": "metamask",
            "data_rows": "",
            "date_field": "",
            "min_timestamp": "",
            "max_timestamp": "",
            "timestamp_resolution": "",
            "timezone_mode": "",
            "timezone_value": "",
            "timezone_conflict": "",
            "source_path": "wallet-state-backup.json",
            "bundle_id": "",
            "bundle_type": "root_file",
            "bundle_relative_path": "wallet-state-backup.json",
            "alias_group": "",
            "collision_status": "",
            "path_scope_tokens": "",
            "content_scope_tokens": "",
            "scope_tokens": "",
            "scope_preview": "",
        }
    ]


def test_build_file_inventory_classifies_binance_specialized_families(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "Binance-Convert-Order-History-202603230441(UTC--6)_abcd.csv").write_text(
        "Time,Wallet,Pair,Type,Sell,Buy,Price,Inverse Price,Date Updated,Status\n",
        encoding="utf-8",
    )
    (raw_dir / "Binance-Fiat-Buy-History-202603230414(UTC--6)_abcd.csv").write_text(
        "Time,Method,Spend Amount,Receive Amount,Fee,Price,Status,Transaction ID\n",
        encoding="utf-8",
    )
    (raw_dir / "Binance-Deposit-History-202603230411(UTC--6)_abcd.csv").write_text(
        "Time,Coin,Network,Amount,Address,TXID,Status\n",
        encoding="utf-8",
    )

    inventory = pipeline_common.build_file_inventory(raw_dir)

    by_name = {row["filename"]: row for row in inventory}
    assert by_name["Binance-Convert-Order-History-202603230441(UTC--6)_abcd.csv"]["family"] == "convert_order_csv"
    assert by_name["Binance-Fiat-Buy-History-202603230414(UTC--6)_abcd.csv"]["family"] == "fiat_buy_csv"
    assert by_name["Binance-Deposit-History-202603230411(UTC--6)_abcd.csv"]["family"] == "deposit_history_csv"


def test_parse_candidate_timestamp_accepts_two_digit_binance_year() -> None:
    parsed = pipeline_common.parse_candidate_timestamp("23-09-20 18:20:55")

    assert parsed is not None
    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == "2023-09-20 18:20:55"


def test_parse_candidate_timestamp_applies_source_timezone() -> None:
    parsed = pipeline_common.parse_candidate_timestamp(
        "23-09-20 18:20:55",
        source_timezone=pipeline_common.source_timezone_from_filename("Binance-Spot-Trade-History-202603230406(UTC--6)_5d63c10c.csv"),
    )

    assert parsed is not None
    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == "2023-09-21 00:20:55"


def test_build_file_inventory_converts_binance_filename_timezone_to_utc(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "Binance-Spot-Trade-History-202603230406(UTC--6)_abcd.csv").write_text(
        "Time,Pair,Side,Price,Executed,Amount,Fee\n"
        "23-09-20 18:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n",
        encoding="utf-8",
    )

    inventory = pipeline_common.build_file_inventory(raw_dir)

    row = inventory[0]
    assert row["min_timestamp"] == "2023-09-21 00:20:55"
    assert row["max_timestamp"] == "2023-09-21 00:20:55"
    assert row["timezone_mode"] == "filename_offset"
    assert row["timezone_value"] == "UTC-06:00"


def test_build_file_inventory_detects_header_utc_and_date_only_modes(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "crypto_transactions.csv").write_text(
        "Timestamp (UTC),Amount\n2021-07-06 17:37:09,1\n",
        encoding="utf-8",
    )
    (raw_dir / "activities-export.csv").write_text(
        "transaction_date,settlement_date,account_type\n2021-05-09,,Crypto\n",
        encoding="utf-8",
    )

    inventory = pipeline_common.build_file_inventory(raw_dir)

    by_name = {row["filename"]: row for row in inventory}
    assert by_name["crypto_transactions.csv"]["timezone_mode"] == "header_utc"
    assert by_name["crypto_transactions.csv"]["timezone_value"] == "UTC"
    assert by_name["activities-export.csv"]["timezone_mode"] == "date_only"
    assert by_name["activities-export.csv"]["timestamp_resolution"] == "date_only"


def test_build_file_inventory_ignores_placeholder_no_data_rows(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "Binance-Futures-Order-History-202603230503(UTC--6)_abcd.csv").write_text(
        "Uid,Time,Order No\nNo data matches the criteria.\n",
        encoding="utf-8",
    )

    inventory = pipeline_common.build_file_inventory(raw_dir)

    row = inventory[0]
    assert row["data_rows"] == "0"
    assert row["date_field"] == ""
    assert row["timezone_mode"] == ""


def test_validate_canonical_event_row_requires_minimum_fields() -> None:
    row = {header: "" for header in pipeline_common.CANONICAL_EVENT_HEADERS}
    row.update(
        {
            "event_id": "evt-1",
            "source": "Coinbase",
            "timestamp": "2026-03-24 10:11:12",
            "event_kind": "Trade",
            "confidence": "high",
            "status": "mapped",
        }
    )

    pipeline_common.validate_canonical_event_row(row)

    row["event_id"] = ""
    with pytest.raises(ValueError, match="event_id"):
        pipeline_common.validate_canonical_event_row(row)


def test_filter_rows_by_timestamp_window_keeps_only_rows_inside_bounds() -> None:
    rows = [
        {"timestamp": "2023-08-05 08:34:04", "event_id": "before"},
        {"timestamp": "2023-08-05 08:34:05", "event_id": "start"},
        {"timestamp": "2025-12-31 23:59:59", "event_id": "end"},
        {"timestamp": "2026-01-01 00:00:00", "event_id": "after"},
    ]

    included, excluded = pipeline_common.filter_rows_by_timestamp_window(
        rows,
        timestamp_key="timestamp",
        window_start="2023-08-05 08:34:05",
        window_end="2025-12-31 23:59:59",
    )

    assert [row["event_id"] for row in included] == ["start", "end"]
    assert [row["event_id"] for row in excluded] == ["before", "after"]
