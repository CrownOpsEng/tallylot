from __future__ import annotations

import json
from pathlib import Path

from tallylot.application.profiling.artifacts import write_profile_artifacts
from tallylot.application.profiling.csv_inventory import infer_date_only_format
from tallylot.application.profiling.inventory import (
    _inventory_file_details,
    build_inventory,
)
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
    assert details.observed_period_start == "2023-09-21"
    assert details.observed_period_end == "2023-09-21"
    assert details.observed_period_label == "2023-09"
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
    assert utc_details.observed_period_start == "2021-07-06"
    assert utc_details.observed_period_end == "2021-07-06"
    assert date_only_details.timezone_mode == "date_only"
    assert date_only_details.timestamp_resolution == "date_only"
    assert date_only_details.min_timestamp == "2021-05-09 00:00:00"
    assert date_only_details.observed_period_start == "2021-05-09"
    assert date_only_details.observed_period_end == "2021-05-09"


def test_inventory_file_details_anchors_day_first_dates_to_matching_filename_date(
    tmp_path: Path,
) -> None:
    path = tmp_path / "2023-05-06 My_Trading_History_Report.csv"
    path.write_text(
        "DATE,PAIR,ADDR,DESCRIPTION,PNL\n06/05/2023,BTCUSD,bb4d,profit,10\n",
        encoding="utf-8",
    )

    _, row_count, details = _inventory_file_details(path)

    assert row_count == 1
    assert details.date_field == "DATE"
    assert details.timestamp_resolution == "date_only"
    assert details.timezone_mode == "date_only"
    assert details.min_timestamp == "2023-05-06 00:00:00"
    assert details.max_timestamp == "2023-05-06 00:00:00"


def test_inventory_file_details_detects_day_first_slash_dates_from_component_bounds(
    tmp_path: Path,
) -> None:
    path = tmp_path / "trading-history.csv"
    path.write_text(
        "DATE,PAIR,ADDR,DESCRIPTION,PNL\n13/05/2023,BTCUSD,bb4d,profit,10\n",
        encoding="utf-8",
    )

    _, row_count, details = _inventory_file_details(path)

    assert row_count == 1
    assert details.timestamp_resolution == "date_only"
    assert details.timezone_mode == "date_only"
    assert details.min_timestamp == "2023-05-13 00:00:00"


def test_inventory_file_details_detects_month_first_slash_dates_from_component_bounds(
    tmp_path: Path,
) -> None:
    path = tmp_path / "trading-history.csv"
    path.write_text(
        "DATE,PAIR,ADDR,DESCRIPTION,PNL\n05/13/2023,BTCUSD,bb4d,profit,10\n",
        encoding="utf-8",
    )

    _, row_count, details = _inventory_file_details(path)

    assert row_count == 1
    assert details.timestamp_resolution == "date_only"
    assert details.timezone_mode == "date_only"
    assert details.min_timestamp == "2023-05-13 00:00:00"


def test_inventory_file_details_uses_chronology_when_only_one_slash_format_preserves_order(
    tmp_path: Path,
) -> None:
    path = tmp_path / "trading-history.csv"
    path.write_text(
        "DATE,PAIR,ADDR,DESCRIPTION,PNL\n"
        "02/03/2023,BTCUSD,bb4d,profit,10\n"
        "03/02/2023,BTCUSD,bb4d,profit,11\n"
        "03/03/2023,BTCUSD,bb4d,profit,12\n",
        encoding="utf-8",
    )

    _, row_count, details = _inventory_file_details(path)

    assert row_count == 3
    assert details.timestamp_resolution == "date_only"
    assert details.timezone_mode == "date_only"
    assert details.min_timestamp == "2023-02-03 00:00:00"
    assert details.max_timestamp == "2023-03-03 00:00:00"


def test_inventory_file_details_anchors_month_first_dates_to_matching_filename_date(
    tmp_path: Path,
) -> None:
    path = tmp_path / "2023-12-05 trading-history.csv"
    path.write_text(
        "DATE,PAIR,ADDR,DESCRIPTION,PNL\n12/05/2023,BTCUSD,bb4d,profit,10\n",
        encoding="utf-8",
    )

    _, row_count, details = _inventory_file_details(path)

    assert row_count == 1
    assert details.timestamp_resolution == "date_only"
    assert details.timezone_mode == "date_only"
    assert details.min_timestamp == "2023-12-05 00:00:00"


def test_infer_date_only_format_rejects_monthly_first_of_month_sequence() -> None:
    assert infer_date_only_format(["01/02/2023", "01/03/2023", "01/04/2023"]) is None


def test_infer_date_only_format_rejects_sparse_chronology_with_large_gaps() -> None:
    assert infer_date_only_format(["02/03/2023", "03/02/2023", "04/02/2023"]) is None


def test_infer_date_only_format_rejects_chronology_with_near_year_gap() -> None:
    assert infer_date_only_format(["02/03/2023", "03/02/2023", "03/02/2024"]) is None


def test_infer_date_only_format_rejects_chronology_with_just_over_year_gap() -> None:
    assert infer_date_only_format(["02/03/2024", "03/02/2024", "03/02/2025"]) is None


def test_infer_date_only_format_rejects_ambiguous_slash_sequence_without_decisive_signal() -> (
    None
):
    assert infer_date_only_format(["06/05/2023", "07/05/2023", "08/05/2023"]) is None


def test_infer_date_only_format_uses_one_day_witness_to_distinguish_day_and_month() -> (
    None
):
    assert (
        infer_date_only_format(["01/02/2023", "02/02/2023", "01/03/2023"]) == "%d/%m/%Y"
    )


def test_infer_date_only_format_uses_filename_anchor_for_month_first_dates() -> None:
    assert (
        infer_date_only_format(
            ["12/05/2023"],
            filename="2023-12-05 trading-history.csv",
        )
        == "%m/%d/%Y"
    )


def test_inventory_file_details_leaves_ambiguous_slash_dates_unclassified_without_filename_anchor(
    tmp_path: Path,
) -> None:
    path = tmp_path / "trading-history.csv"
    path.write_text(
        "DATE,PAIR,ADDR,DESCRIPTION,PNL\n06/05/2023,BTCUSD,bb4d,profit,10\n",
        encoding="utf-8",
    )

    _, row_count, details = _inventory_file_details(path)

    assert row_count == 1
    assert details.date_field == "DATE"
    assert details.timestamp_resolution == "unknown"
    assert details.timezone_mode == "naive"
    assert details.min_timestamp == ""
    assert details.max_timestamp == ""


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


def test_inventory_file_details_prefers_earliest_plausible_header_row(
    tmp_path: Path,
) -> None:
    path = tmp_path / "Wallet-eth portfolio.csv"
    path.write_text(
        "Chain,Token,Portfolio %,Price,Amount,Value\n"
        "ETH,Ether (ETH),100.00%,$2,142.73,0.00178571,$3.83\n",
        encoding="utf-8",
    )

    header, row_count, details = _inventory_file_details(path)

    assert header == ("Chain", "Token", "Portfolio %", "Price", "Amount", "Value")
    assert row_count == 1
    assert details.date_field == ""


def test_build_inventory_enriches_rows_from_capture_metadata(tmp_path: Path) -> None:
    raw_dir = (
        tmp_path
        / "workspace"
        / "evidence"
        / "raw"
        / "source"
        / "eth-wallet-fixture"
        / "2026-03"
    )
    raw_dir.mkdir(parents=True)
    (raw_dir / "capture.json").write_text(
        json.dumps(
            {
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "source": "eth-wallet-fixture",
                "capture_label": "2026-03",
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/eth-wallet-fixture",
                "manifest_fingerprint": "manifest:fixture",
                "status": "captured",
                "notes": "",
            }
        ),
        encoding="utf-8",
    )
    (raw_dir / "transactions.csv").write_text(
        "Timestamp,Amount\n2026-03-23 15:47:00-06:00,1\n",
        encoding="utf-8",
    )

    inventory, issues = build_inventory(raw_dir, inspect_archives=True)

    assert issues == []
    assert inventory[0].capture_uid == "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    assert inventory[0].source == "eth-wallet-fixture"
    assert inventory[0].observed_period_start == "2026-03-23"
    assert inventory[0].observed_period_end == "2026-03-23"
    assert inventory[0].observed_period_label == "2026-03"


def test_build_inventory_excludes_capture_control_artifacts(tmp_path: Path) -> None:
    raw_dir = (
        tmp_path / "workspace" / "evidence" / "raw" / "source" / "binance" / "capture"
    )
    raw_dir.mkdir(parents=True)
    (raw_dir / "capture.json").write_text(
        json.dumps(
            {
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "source": "binance",
                "capture_label": "capture",
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/binance",
                "manifest_fingerprint": "manifest:fixture",
                "status": "captured",
                "notes": "",
            }
        ),
        encoding="utf-8",
    )
    (raw_dir / "manifest.csv").write_text(
        "relative_path,sha256,size_bytes\n", encoding="utf-8"
    )
    (raw_dir / "manifest_issues.csv").write_text(
        "relative_path,kind,message\n",
        encoding="utf-8",
    )
    (raw_dir / "transactions.csv").write_text(
        "Timestamp,Amount\n2026-03-23 15:47:00-06:00,1\n",
        encoding="utf-8",
    )

    inventory, issues = build_inventory(raw_dir, inspect_archives=True)

    assert issues == []
    assert [entry.relative_path for entry in inventory] == ["transactions.csv"]


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
