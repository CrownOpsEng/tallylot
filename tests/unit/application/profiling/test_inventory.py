from __future__ import annotations

from pathlib import Path

from tallylot.application.profiling.artifacts import write_profile_artifacts
from tallylot.application.profiling.inventory import _inventory_file_details
from tallylot.domain.types import AdapterId, SourceId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.source_profiles import (
    PROFILE_INVENTORY_HEADER,
    FileInventoryEntry,
    SourceProfile,
)


def test_inventory_file_details_applies_binance_filename_offset_to_min_and_max(
    tmp_path: Path,
) -> None:
    path = tmp_path / "Binance-Spot-Trade-History-202603230406(UTC--6)_abcd.csv"
    path.write_text(
        "Time,Pair,Side,Price,Executed,Amount,Fee\n"
        "23-09-20 18:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n"
        "23-09-20 19:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n",
        encoding="utf-8",
    )

    _, row_count, details = _inventory_file_details(path)

    assert row_count == 2
    assert details.min_timestamp == "2023-09-21 00:20:55"
    assert details.max_timestamp == "2023-09-21 01:20:55"
    assert details.timezone_mode == "filename_offset"
    assert details.timezone_value == "UTC-06:00"


def test_inventory_file_details_detects_header_utc_and_date_only_modes(
    tmp_path: Path,
) -> None:
    utc_path = tmp_path / "crypto_transactions.csv"
    utc_path.write_text(
        "Timestamp (UTC),Amount\n2021-07-06 17:37:09,1\n",
        encoding="utf-8",
    )
    date_only_path = tmp_path / "activities-export.csv"
    date_only_path.write_text(
        "transaction_date,settlement_date,account_type\n2021-05-09,,Crypto\n",
        encoding="utf-8",
    )

    _, _, utc_details = _inventory_file_details(utc_path)
    _, _, date_only_details = _inventory_file_details(date_only_path)

    assert utc_details.timezone_mode == "header_utc"
    assert utc_details.timezone_value == "UTC"
    assert utc_details.min_timestamp == "2021-07-06 17:37:09"
    assert date_only_details.timezone_mode == "date_only"
    assert date_only_details.timestamp_resolution == "date_only"
    assert date_only_details.min_timestamp == "2021-05-09 00:00:00"


def test_inventory_file_details_ignores_placeholder_no_data_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / "Binance-Futures-Order-History-202603230503(UTC--6)_abcd.csv"
    path.write_text(
        "Uid,Time,Order No\nNo data matches the criteria.\n",
        encoding="utf-8",
    )

    _, row_count, details = _inventory_file_details(path)

    assert row_count == 0
    assert details.date_field == "Time"
    assert details.min_timestamp == ""
    assert details.timezone_mode == ""


def test_inventory_file_details_skips_coinbase_retail_preamble_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / "retail-export.csv"
    path.write_text(
        "\n"
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,"
        "Price Currency,Price at Transaction,Subtotal,"
        "Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,"
        "$60000.00,$600.00,$610.00,$10.00,Bought 0.01 BTC for 610 CAD\n",
        encoding="utf-8",
    )

    header, row_count, details = _inventory_file_details(path)

    assert header[0] == "ID"
    assert "Timestamp" in header
    assert row_count == 1
    assert details.date_field == "Timestamp"
    assert details.min_timestamp == "2024-02-08 16:31:22"
    assert details.timezone_mode == "value_utc"


def test_inventory_file_details_accepts_fractional_second_utc_timestamps(
    tmp_path: Path,
) -> None:
    path = tmp_path / "coinbase-pro-statement.csv"
    path.write_text(
        "portfolio,type,time,amount,balance,amount/balance unit,transfer id,trade id,order id\n"
        "default,deposit,2021-05-10T02:37:18.689Z,0.0321777400000000,0.0321777400000000,ETH,tx-1,,\n",
        encoding="utf-8",
    )

    _, row_count, details = _inventory_file_details(path)

    assert row_count == 1
    assert details.date_field == "time"
    assert details.min_timestamp == "2021-05-10 02:37:18"
    assert details.max_timestamp == "2021-05-10 02:37:18"
    assert details.timezone_mode == "value_utc"


def test_inventory_file_details_ignores_footer_rows_with_as_of_text(
    tmp_path: Path,
) -> None:
    path = tmp_path / "activities-export.csv"
    path.write_text(
        'transaction_date,settlement_date,account_type\n2021-05-09,,Crypto\n\n"As of 2026-03-23 15:47 GMT-06:00"\n',
        encoding="utf-8",
    )

    _, row_count, details = _inventory_file_details(path)

    assert row_count == 2
    assert details.date_field == "transaction_date"
    assert details.min_timestamp == "2021-05-09 00:00:00"
    assert details.max_timestamp == "2021-05-09 00:00:00"
    assert details.timezone_mode == "date_only"


def test_inventory_file_details_converts_explicit_offsets_to_utc(
    tmp_path: Path,
) -> None:
    path = tmp_path / "offset-timestamps.csv"
    path.write_text(
        "Timestamp,Amount\n2026-03-23 15:47:00-06:00,1\n",
        encoding="utf-8",
    )

    _, row_count, details = _inventory_file_details(path)

    assert row_count == 1
    assert details.date_field == "Timestamp"
    assert details.min_timestamp == "2026-03-23 21:47:00"
    assert details.max_timestamp == "2026-03-23 21:47:00"


def test_profile_inventory_writer_emits_capture_scoped_columns(tmp_path: Path) -> None:
    profile = SourceProfile(
        source=SourceId("binance"),
        raw_dir=str(tmp_path / "raw"),
        adapter_id=AdapterId("binance"),
        manifest_fingerprint="manifest:fixture",
        file_inventory=(
            FileInventoryEntry(
                relative_path="statement.pdf",
                suffix=".pdf",
                size_bytes=1024,
                sha256="fixture",
                capture_uid="01HV4A5H7VJH7M3Y5A6B7C8D9E",
                source="binance",
                evidence_role="statement",
                observed_period_start="2026-01-01",
                observed_period_end="2026-03-23",
                observed_period_label="2026-Q1",
                statement_kind="balance_statement",
                originality_class="original",
            ),
        ),
        supported=True,
    )
    artifacts = FilesystemArtifactStore()
    output_dir = tmp_path / "profile"

    write_profile_artifacts(artifacts, profile, output_dir)

    rows = artifacts.read_rows(output_dir / "profile_inventory.csv")

    assert tuple(rows[0].keys()) == PROFILE_INVENTORY_HEADER
    assert rows[0]["capture_uid"] == "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    assert rows[0]["evidence_role"] == "statement"
