from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from crypto_reconciliation.application.dtos import BaselineValidateRequest
from crypto_reconciliation.application.services.baseline import (
    BaselineValidationService,
    build_asset_snapshot,
    build_cad_flow_summary,
    build_exchange_reconciliation,
    build_source_activity,
    decimal_text,
    find_required_baseline_exports,
    latest_trade_timestamp,
    parse_trade_table_row,
)
from crypto_reconciliation.application.services.export_files import find_required_csv_export, find_required_csv_exports
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_find_required_baseline_exports_uses_shared_helper_behavior(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    for stem in (
        "Trade Table",
        "Current Balance",
        "Balance by Exchange",
        "Validate Transactions",
        "Missing Transactions",
        "Duplicate Transactions",
    ):
        (export_dir / f"{stem}.csv").write_text("col\n", encoding="utf-8")

    assert find_required_baseline_exports(export_dir) == find_required_csv_exports(
        export_dir,
        (
            "Trade Table",
            "Current Balance",
            "Balance by Exchange",
            "Validate Transactions",
            "Missing Transactions",
            "Duplicate Transactions",
        ),
    )


def test_find_required_csv_export_rejects_ambiguous_matches(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    (export_dir / "Trade Table A.csv").write_text("x\n", encoding="utf-8")
    (export_dir / "Trade Table B.csv").write_text("x\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Ambiguous export"):
        find_required_csv_export(export_dir, "Trade Table")


def test_decimal_text_quantizes_to_eight_places() -> None:
    assert decimal_text(Decimal("1.234567891")) == "1.23456789"
    assert decimal_text(Decimal("-0.00000001")) == "-0.00000001"


def test_parse_trade_table_row_treats_blank_numeric_fields_as_zero() -> None:
    assert parse_trade_table_row(["Trade", "", "BTC", "", "CAD", "", "CAD"]) == (
        "Trade",
        Decimal("0"),
        "BTC",
        Decimal("0"),
        "CAD",
        Decimal("0"),
        "CAD",
    )


def test_parse_trade_table_row_rejects_short_rows() -> None:
    with pytest.raises(ValueError, match="too short"):
        parse_trade_table_row(["Trade", "1"])


def test_build_asset_snapshot_sorts_and_tracks_negative_balances() -> None:
    rows, current_by_ticker, negative_balances = build_asset_snapshot(
        current_rows=[
            {"Ticker": "BTC", "Name": "Bitcoin", "Type": "Coin", "Amount": "1.50000000", "Value in CAD": "100000"},
            {
                "Ticker": "CAD",
                "Name": "Canadian Dollar",
                "Type": "Currency",
                "Amount": "-12.34000000",
                "Value in CAD": "-12.34",
            },
        ],
        exchange_rows=[
            {"Amount": "1.50000000", "Currency": "BTC", "Current value in CAD": "100000", "Exchange": "Coinbase"},
            {"Amount": "-12.34000000", "Currency": "CAD", "Current value in CAD": "-12.34", "Exchange": "Bank"},
        ],
    )

    assert [row["ticker"] for row in rows] == ["BTC", "CAD"]
    assert current_by_ticker["BTC"] == Decimal("1.50000000")
    assert negative_balances[0]["ticker"] == "CAD"
    assert negative_balances[0]["amount"] == "-12.34000000"


def test_build_exchange_reconciliation_detects_drift_and_cad_rows() -> None:
    rows, cad_rows, max_difference, max_ticker = build_exchange_reconciliation(
        current_by_ticker={"BTC": Decimal("1.0"), "CAD": Decimal("-5.0")},
        exchange_rows=[
            {"Amount": "0.4", "Currency": "BTC", "Current value in CAD": "1", "Exchange": "A"},
            {"Amount": "0.7", "Currency": "BTC", "Current value in CAD": "2", "Exchange": "B"},
            {"Amount": "-5.0", "Currency": "CAD", "Current value in CAD": "-5", "Exchange": "Bank"},
        ],
    )

    btc_row = next(row for row in rows if row["ticker"] == "BTC")
    assert btc_row["status"] == "drift"
    assert btc_row["difference"] == "0.10000000"
    assert cad_rows[0]["exchange"] == "Bank"
    assert max_difference == Decimal("0.1")
    assert max_ticker == "BTC"


def test_build_exchange_reconciliation_includes_exchange_only_assets() -> None:
    rows, cad_rows, max_difference, max_ticker = build_exchange_reconciliation(
        current_by_ticker={"BTC": Decimal("1.0")},
        exchange_rows=[{"Amount": "2.0", "Currency": "ETH", "Current value in CAD": "5000", "Exchange": "Wallet"}],
    )

    eth_row = next(row for row in rows if row["ticker"] == "ETH")
    assert eth_row["current_balance_amount"] == "0.00000000"
    assert eth_row["balance_by_exchange_amount"] == "2.00000000"
    assert eth_row["difference"] == "2.00000000"
    assert eth_row["status"] == "drift"
    assert cad_rows == []
    assert max_difference == Decimal("2.0")
    assert max_ticker == "ETH"


def test_build_source_activity_merges_trade_and_balance_views() -> None:
    rows = build_source_activity(
        trade_rows=[
            {"Exchange": "Wallet A", "Date": "2023-08-01 00:00:00"},
            {"Exchange": "Wallet A", "Date": "2023-08-05 08:34:04"},
            {"Exchange": "Wallet B", "Date": "2023-08-03 00:00:00"},
        ],
        exchange_rows=[
            {"Exchange": "Wallet A", "Currency": "BTC"},
            {"Exchange": "Wallet A", "Currency": "ETH"},
            {"Exchange": "Wallet C", "Currency": "ADA"},
        ],
    )

    wallet_a = next(row for row in rows if row["source"] == "Wallet A")
    wallet_c = next(row for row in rows if row["source"] == "Wallet C")

    assert wallet_a["first_trade_timestamp"] == "2023-08-01 00:00:00"
    assert wallet_a["last_trade_timestamp"] == "2023-08-05 08:34:04"
    assert wallet_a["trade_table_rows"] == "2"
    assert wallet_a["balance_asset_count"] == "2"
    assert wallet_a["present_in_trade_table"] == "yes"
    assert wallet_a["present_in_balance_by_exchange"] == "yes"
    assert wallet_c["first_trade_timestamp"] == ""
    assert wallet_c["trade_table_rows"] == "0"
    assert wallet_c["balance_by_exchange_rows"] == "1"
    assert wallet_c["present_in_trade_table"] == "no"
    assert wallet_c["present_in_balance_by_exchange"] == "yes"


def test_build_cad_flow_summary_aggregates_by_type() -> None:
    rows, cad_bought_total, cad_sold_total, cad_fee_total = build_cad_flow_summary(
        trade_rows=[
            {
                "Type": "Trade",
                "Buy": "100.00",
                "Cur.": "CAD",
                "Sell": "1.0",
                "Cur..1": "BTC",
                "Fee": "2.00",
                "Cur..2": "CAD",
            },
            {
                "Type": "Trade",
                "Buy": "0.5",
                "Cur.": "BTC",
                "Sell": "50.00",
                "Cur..1": "CAD",
                "Fee": "0.50",
                "Cur..2": "CAD",
            },
            {
                "Type": "Income",
                "Buy": "25.00",
                "Cur.": "CAD",
                "Sell": "0",
                "Cur..1": "",
                "Fee": "0",
                "Cur..2": "",
            },
        ]
    )

    assert cad_bought_total == Decimal("125.00")
    assert cad_sold_total == Decimal("50.00")
    assert cad_fee_total == Decimal("2.50")
    trade_row = next(row for row in rows if row["type"] == "Trade")
    assert trade_row["cad_bought"] == "100.00000000"
    assert trade_row["cad_sold"] == "50.00000000"


def test_build_cad_flow_summary_returns_zero_totals_without_cad_rows() -> None:
    rows, cad_bought_total, cad_sold_total, cad_fee_total = build_cad_flow_summary(
        trade_rows=[
            {
                "Type": "Trade",
                "Buy": "1.0",
                "Cur.": "BTC",
                "Sell": "2.0",
                "Cur..1": "ETH",
                "Fee": "0.01",
                "Cur..2": "BTC",
            }
        ]
    )

    assert rows == []
    assert cad_bought_total == Decimal("0")
    assert cad_sold_total == Decimal("0")
    assert cad_fee_total == Decimal("0")


def test_latest_trade_timestamp_requires_dated_rows() -> None:
    with pytest.raises(ValueError, match="did not contain any dated rows"):
        latest_trade_timestamp([{"Date": ""}])


def test_latest_trade_timestamp_returns_latest_row() -> None:
    latest = latest_trade_timestamp(
        [
            {"Date": "2023-08-05 08:33:00"},
            {"Date": "2023-08-05 08:34:04"},
            {"Date": "2023-08-05 08:34:03"},
        ]
    )

    assert latest.strftime("%Y-%m-%d %H:%M:%S") == "2023-08-05 08:34:04"


def test_latest_trade_timestamp_rejects_malformed_timestamp() -> None:
    with pytest.raises(ValueError):
        latest_trade_timestamp([{"Date": "2023/08/05 08:34:04"}])


def test_baseline_validation_service_writes_relocation_safe_artifacts(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "baseline"

    response = BaselineValidationService(FilesystemArtifactStore()).execute(
        BaselineValidateRequest(export_dir=baseline_export_dir, output_dir=output_dir)
    )

    store = FilesystemArtifactStore()
    reconciliation_rows = store.read_rows(output_dir / "baseline_exchange_reconciliation.csv")
    summary = json.loads((output_dir / "baseline_summary.json").read_text(encoding="utf-8"))

    assert response.asset_count >= 1
    assert any(row["ticker"] == "CAD" for row in reconciliation_rows)
    assert summary["latest_transaction_timestamp"] == response.latest_timestamp
    assert "max_asset_difference" in summary
    assert "ending_cad_balance" in summary
    assert output_dir.joinpath("baseline_source_activity.csv").exists()
