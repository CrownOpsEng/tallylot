from __future__ import annotations

import contextlib
import io
import json
from decimal import Decimal
from pathlib import Path

import pytest

import baseline_check
import script_common
from tests.support.helpers import read_dict_rows, write_csv


def write_minimal_baseline_exports(export_dir: Path) -> None:
    write_csv(
        export_dir / "Trade Table.csv",
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date"],
        [["Trade", "1.0", "BTC", "10.0", "CAD", "0.5", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04"]],
    )
    write_csv(
        export_dir / "Current Balance.csv",
        ["Ticker", "Name", "Type", "Amount", "Value in CAD"],
        [["BTC", "Bitcoin", "Coin", "1.00000000", "10.00"], ["CAD", "Canadian Dollar", "Currency", "-10.00000000", "-10.00"]],
    )
    write_csv(
        export_dir / "Balance by Exchange.csv",
        ["Amount", "Currency", "Current value in CAD", "Current value in BTC", "Exchange"],
        [["1.00000000", "BTC", "10.00", "0.1", "Coinbase"], ["-10.00000000", "CAD", "-10.00", "-0.1", "Coinbase"]],
    )
    write_csv(export_dir / "Validate Transactions.csv", ["Issue"], [["AXS"]])
    write_csv(export_dir / "Missing Transactions.csv", ["Issue"], [["Missing"]])
    write_csv(export_dir / "Duplicate Transactions.csv", ["Issue"], [])


def test_find_required_files_rejects_missing_required_export(tmp_path: Path) -> None:
    export_dir = tmp_path
    write_csv(
        export_dir / "Trade Table.csv",
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date"],
        [["Trade", "1", "BTC", "10", "CAD", "0", "CAD", "X", "", "", "2023-08-05 08:34:04"]],
    )
    for marker in ["Current Balance", "Validate Transactions", "Missing Transactions", "Duplicate Transactions"]:
        write_csv(export_dir / f"{marker}.csv", ["A"], [["1"]])

    with pytest.raises(FileNotFoundError, match="Balance by Exchange"):
        baseline_check.find_required_files(export_dir)


def test_find_required_files_rejects_ambiguous_match(tmp_path: Path) -> None:
    export_dir = tmp_path
    for name in ["a Trade Table.csv", "b Trade Table.csv"]:
        write_csv(
            export_dir / name,
            ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date"],
            [["Trade", "1", "BTC", "10", "CAD", "0", "CAD", "X", "", "", "2023-08-05 08:34:04"]],
        )
    for marker in ["Current Balance", "Balance by Exchange", "Validate Transactions", "Missing Transactions", "Duplicate Transactions"]:
        write_csv(export_dir / f"{marker}.csv", ["A"], [["1"]])

    with pytest.raises(ValueError, match="Ambiguous export"):
        baseline_check.find_required_files(export_dir)


def test_decimal_text_quantizes_to_eight_places() -> None:
    assert baseline_check.decimal_text(Decimal("1.234567891")) == "1.23456789"
    assert baseline_check.decimal_text(Decimal("-0.00000001")) == "-0.00000001"


def test_find_required_files_uses_shared_helper_behavior(tmp_path: Path) -> None:
    export_dir = tmp_path
    for marker in baseline_check.REQUIRED_FILES.values():
        write_csv(export_dir / f"{marker}.csv", ["A"], [["1"]])

    assert baseline_check.find_required_files(export_dir) == script_common.find_required_csv_exports(
        export_dir,
        baseline_check.REQUIRED_FILES,
        "Export directory",
    )


def test_parse_trade_table_row_treats_blank_numeric_fields_as_zero() -> None:
    parsed = baseline_check.parse_trade_table_row(
        ["Trade", "", "BTC", "", "CAD", "", "CAD", "X", "", "", "2023-08-05 08:34:04"]
    )

    assert parsed == ("Trade", Decimal("0"), "BTC", Decimal("0"), "CAD", Decimal("0"), "CAD")


def test_build_asset_snapshot_sorts_and_tracks_negative_balances() -> None:
    rows = [
        {"Ticker": "BTC", "Name": "Bitcoin", "Type": "Coin", "Amount": "1.50000000", "Value in CAD": "100000"},
        {"Ticker": "CAD", "Name": "Canadian Dollar", "Type": "Currency", "Amount": "-12.34000000", "Value in CAD": "-12.34"},
    ]

    snapshot_rows, current_by_ticker, negative_balances = baseline_check.build_asset_snapshot(rows)

    assert [row["ticker"] for row in snapshot_rows] == ["BTC", "CAD"]
    assert current_by_ticker["BTC"] == Decimal("1.50000000")
    assert negative_balances[0]["ticker"] == "CAD"
    assert negative_balances[0]["amount"] == "-12.34000000"


def test_build_exchange_reconciliation_detects_drift_and_cad_rows() -> None:
    current_by_ticker = {"BTC": Decimal("1.0"), "CAD": Decimal("-5.0")}
    exchange_rows = [
        {"Amount": "0.4", "Currency": "BTC", "Current value in CAD": "1", "Exchange": "A"},
        {"Amount": "0.7", "Currency": "BTC", "Current value in CAD": "2", "Exchange": "B"},
        {"Amount": "-5.0", "Currency": "CAD", "Current value in CAD": "-5", "Exchange": "Bank"},
    ]

    reconciliation_rows, cad_rows, max_difference, max_ticker = baseline_check.build_exchange_reconciliation(
        current_by_ticker,
        exchange_rows,
    )

    btc_row = next(row for row in reconciliation_rows if row["ticker"] == "BTC")
    assert btc_row["status"] == "drift"
    assert btc_row["difference"] == "0.10000000"
    assert cad_rows[0]["exchange"] == "Bank"
    assert max_difference == Decimal("0.1")
    assert max_ticker == "BTC"


def test_build_exchange_reconciliation_includes_extra_exchange_only_assets() -> None:
    reconciliation_rows, cad_rows, max_difference, max_ticker = baseline_check.build_exchange_reconciliation(
        {"BTC": Decimal("1.0")},
        [{"Amount": "2.0", "Currency": "ETH", "Current value in CAD": "5000", "Exchange": "Wallet"}],
    )

    eth_row = next(row for row in reconciliation_rows if row["ticker"] == "ETH")
    assert eth_row["current_balance_amount"] == "0.00000000"
    assert eth_row["balance_by_exchange_amount"] == "2.00000000"
    assert eth_row["difference"] == "2.00000000"
    assert eth_row["status"] == "drift"
    assert cad_rows == []
    assert max_difference == Decimal("2.0")
    assert max_ticker == "ETH"


def test_build_source_activity_merges_trade_and_balance_views() -> None:
    rows = baseline_check.build_source_activity(
        [
            {"Exchange": "Wallet A", "Date": "2023-08-01 00:00:00"},
            {"Exchange": "Wallet A", "Date": "2023-08-05 08:34:04"},
            {"Exchange": "Wallet B", "Date": "2023-08-03 00:00:00"},
        ],
        [
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


def test_build_cad_flow_summary_aggregates_by_type(tmp_path: Path) -> None:
    trade_table = tmp_path / "trade_table.csv"
    write_csv(
        trade_table,
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date"],
        [
            ["Trade", "100.00", "CAD", "1.0", "BTC", "2.00", "CAD", "X", "", "", "2024-01-01 00:00:00"],
            ["Trade", "0.5", "BTC", "50.00", "CAD", "0.50", "CAD", "X", "", "", "2024-01-02 00:00:00"],
            ["Income", "25.00", "CAD", "0", "", "0", "", "X", "", "", "2024-01-03 00:00:00"],
        ],
    )

    cad_flow_rows, cad_bought_total, cad_sold_total, cad_fee_total = baseline_check.build_cad_flow_summary(trade_table)

    assert cad_bought_total == Decimal("125.00")
    assert cad_sold_total == Decimal("50.00")
    assert cad_fee_total == Decimal("2.50")
    trade_row = next(row for row in cad_flow_rows if row["type"] == "Trade")
    assert trade_row["cad_bought"] == "100.00000000"
    assert trade_row["cad_sold"] == "50.00000000"


def test_build_cad_flow_summary_returns_zero_totals_without_cad_rows(tmp_path: Path) -> None:
    trade_table = tmp_path / "trade_table.csv"
    write_csv(
        trade_table,
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date"],
        [["Trade", "1.0", "BTC", "2.0", "ETH", "0.01", "BTC", "X", "", "", "2024-01-01 00:00:00"]],
    )

    cad_flow_rows, cad_bought_total, cad_sold_total, cad_fee_total = baseline_check.build_cad_flow_summary(trade_table)

    assert cad_flow_rows == []
    assert cad_bought_total == Decimal("0")
    assert cad_sold_total == Decimal("0")
    assert cad_fee_total == Decimal("0")


def test_build_baseline_artifacts_from_minimal_export_dir(tmp_path: Path) -> None:
    export_dir = tmp_path
    write_minimal_baseline_exports(export_dir)

    artifacts = baseline_check.build_baseline_artifacts(export_dir)

    assert artifacts["summary"]["latest_transaction_timestamp"] == "2023-08-05 08:34:04"
    assert artifacts["summary"]["current_balance_rows"] == 2
    assert artifacts["summary"]["negative_balance_rows"] == 1
    assert artifacts["summary"]["max_asset_difference"] == "0.00000000"
    assert artifacts["summary"]["max_asset_difference_ticker"] == ""
    assert artifacts["summary"]["ending_cad_balance"] == "-10.00000000"
    assert artifacts["summary"]["cad_bought_total"] == "0.00000000"
    assert artifacts["summary"]["cad_sold_total"] == "10.00000000"
    assert artifacts["summary"]["cad_fee_total"] == "0.50000000"
    assert artifacts["summary"]["asset_reconciliation_assets"] == 2
    assert artifacts["summary"]["trade_table_sources"] == 1
    assert artifacts["summary"]["balance_by_exchange_sources"] == 1
    assert artifacts["summary"]["source_activity_rows"] == 1
    assert artifacts["negative_balances"] == [
        {
            "ticker": "CAD",
            "name": "Canadian Dollar",
            "type": "Currency",
            "amount": "-10.00000000",
            "value_cad": "-10.00",
        }
    ]


def test_latest_trade_timestamp_requires_dated_rows() -> None:
    with pytest.raises(ValueError, match="did not contain any dated rows"):
        baseline_check.latest_trade_timestamp([{"Date": ""}])


def test_latest_trade_timestamp_returns_latest_row() -> None:
    latest = baseline_check.latest_trade_timestamp(
        [
            {"Date": "2023-08-05 08:33:00"},
            {"Date": "2023-08-05 08:34:04"},
            {"Date": "2023-08-05 08:34:03"},
        ]
    )

    assert latest.strftime("%Y-%m-%d %H:%M:%S") == "2023-08-05 08:34:04"


def test_latest_trade_timestamp_rejects_malformed_timestamp() -> None:
    with pytest.raises(ValueError):
        baseline_check.latest_trade_timestamp([{"Date": "2023/08/05 08:34:04"}])


def test_parse_trade_table_row_rejects_short_rows() -> None:
    with pytest.raises(ValueError, match="too short"):
        baseline_check.parse_trade_table_row(["Trade", "1"])


def test_write_baseline_artifacts_creates_expected_files(tmp_path: Path) -> None:
    artifacts = {
        "asset_snapshot_rows": [{"ticker": "BTC", "name": "Bitcoin", "type": "Coin", "amount": "1.0", "value_cad": "1"}],
        "reconciliation_rows": [{"ticker": "BTC", "current_balance_amount": "1.0", "balance_by_exchange_amount": "1.0", "difference": "0.0", "status": "match"}],
        "negative_balances": [],
        "source_activity_rows": [{"source": "Wallet", "first_trade_timestamp": "2023-08-05 08:34:04", "last_trade_timestamp": "2023-08-05 08:34:04", "trade_table_rows": "1", "balance_by_exchange_rows": "1", "balance_asset_count": "1", "present_in_trade_table": "yes", "present_in_balance_by_exchange": "yes"}],
        "cad_flow_rows": [],
        "cad_balance_by_exchange_rows": [],
        "summary": {"latest_transaction_timestamp": "2023-08-05 08:34:04"},
    }

    out_dir = tmp_path
    baseline_check.write_baseline_artifacts(out_dir, artifacts)

    produced = sorted(path.name for path in out_dir.iterdir())
    assert produced == [
        "baseline_asset_snapshot.csv",
        "baseline_cad_balance_by_exchange.csv",
        "baseline_cad_flow_by_type.csv",
        "baseline_exchange_reconciliation.csv",
        "baseline_negative_balances.csv",
        "baseline_source_activity.csv",
        "baseline_summary.json",
    ]
    with (out_dir / "baseline_summary.json").open(encoding="utf-8") as handle:
        assert json.load(handle)["latest_transaction_timestamp"] == "2023-08-05 08:34:04"
    assert read_dict_rows(out_dir / "baseline_asset_snapshot.csv") == [{"ticker": "BTC", "name": "Bitcoin", "type": "Coin", "amount": "1.0", "value_cad": "1"}]
    assert read_dict_rows(out_dir / "baseline_exchange_reconciliation.csv") == [{"ticker": "BTC", "current_balance_amount": "1.0", "balance_by_exchange_amount": "1.0", "difference": "0.0", "status": "match"}]


def test_parse_args_reads_expected_paths() -> None:
    args = baseline_check.parse_args(["--export-dir", "exports", "--out-dir", "out"])

    assert args.export_dir == Path("exports")
    assert args.out_dir == Path("out")


def test_main_writes_artifacts_and_prints_summary_json(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    out_dir = tmp_path / "out"
    export_dir.mkdir()
    write_minimal_baseline_exports(export_dir)

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = baseline_check.main(["--export-dir", str(export_dir), "--out-dir", str(out_dir)])

    summary = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert summary["latest_transaction_timestamp"] == "2023-08-05 08:34:04"
    assert (out_dir / "baseline_summary.json").exists()
