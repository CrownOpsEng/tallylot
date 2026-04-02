from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tools.oracles.cointracking.baseline import find_required_baseline_exports
from tools.oracles.cointracking.baseline.rows import (
    parse_baseline_export_rows,
    read_baseline_export_rows,
)


def test_read_baseline_export_rows_parses_fixture_exports() -> None:
    export_dir = Path("tests/fixtures/baseline_exports")
    rows = read_baseline_export_rows(
        find_required_baseline_exports(export_dir),
        FilesystemArtifactStore(),
    )

    assert rows.trade_rows == (
        {
            "Type": "Trade",
            "Buy": "1.0",
            "Cur.": "BTC",
            "Sell": "10.0",
            "Cur..1": "CAD",
            "Fee": "0.1",
            "Cur..2": "CAD",
            "Exchange": "Fixture",
            "Group": "",
            "Comment": "baseline",
            "Date": "2023-08-05 08:34:04",
            "Tx-ID": "tx-1",
        },
    )
    assert not rows.validate_rows


def test_parse_baseline_export_rows_ignores_blank_unnamed_trailing_column() -> None:
    rows = parse_baseline_export_rows(
        "Missing Transactions",
        [
            {
                "Type": "Missing Deposit",
                "Amount": "1.5",
                "Cur.": "BTC",
                "Fee": "",
                "Fee Cur.": "",
                "Value in CAD": "100",
                "Exchange": "Fixture",
                "Trade Group": "",
                "Comment": "",
                "Trade ID": "m-1",
                "Date": "",
                "Match": "",
                "": "",
            }
        ],
    )

    assert rows[0]["Fee"] == "0"
    assert "" not in rows[0]


def test_parse_baseline_export_rows_returns_immutable_rows() -> None:
    rows = parse_baseline_export_rows(
        "Current Balance",
        [
            {
                "Ticker": "BTC",
                "Name": "Bitcoin",
                "Type": "Coin",
                "Amount": "1",
                "Value in CAD": "100",
            }
        ],
    )

    assert isinstance(rows, tuple)
    with pytest.raises(TypeError):
        rows[0]["Ticker"] = "ETH"  # type: ignore[index]


def test_parse_baseline_export_rows_rejects_malformed_timestamps() -> None:
    with pytest.raises(ValidationError):
        parse_baseline_export_rows(
            "Trade Table",
            [
                {
                    "Type": "Trade",
                    "Buy": "1",
                    "Cur.": "BTC",
                    "Sell": "10",
                    "Cur..1": "CAD",
                    "Fee": "0.1",
                    "Cur..2": "CAD",
                    "Exchange": "Fixture",
                    "Group": "",
                    "Comment": "bad date",
                    "Date": "2023/08/05 08:34:04",
                    "Tx-ID": "tx-1",
                }
            ],
        )


def test_parse_baseline_export_rows_rejects_extra_columns() -> None:
    with pytest.raises(ValidationError):
        parse_baseline_export_rows(
            "Current Balance",
            [
                {
                    "Ticker": "BTC",
                    "Name": "Bitcoin",
                    "Type": "Coin",
                    "Amount": "1",
                    "Value in CAD": "100",
                    "Unexpected": "extra",
                }
            ],
        )


def test_parse_baseline_export_rows_rejects_unknown_export_family() -> None:
    with pytest.raises(
        ValueError, match="Unsupported CoinTracking baseline export family"
    ):
        parse_baseline_export_rows("Unsupported Report", [])


def test_parse_baseline_export_rows_requires_csv_aliases() -> None:
    with pytest.raises(ValidationError):
        parse_baseline_export_rows(
            "Current Balance",
            [
                {
                    "ticker": "BTC",
                    "name": "Bitcoin",
                    "asset_type": "Coin",
                    "amount": "1",
                    "value_cad": "100",
                }
            ],
        )


def test_parse_baseline_export_rows_rejects_blank_required_identifiers() -> None:
    with pytest.raises(ValidationError, match="ticker must not be blank"):
        parse_baseline_export_rows(
            "Current Balance",
            [
                {
                    "Ticker": "",
                    "Name": "Bitcoin",
                    "Type": "Coin",
                    "Amount": "1",
                    "Value in CAD": "100",
                }
            ],
        )


def test_parse_baseline_export_rows_rejects_blank_required_amounts() -> None:
    with pytest.raises(ValidationError, match="amount must not be blank"):
        parse_baseline_export_rows(
            "Current Balance",
            [
                {
                    "Ticker": "BTC",
                    "Name": "Bitcoin",
                    "Type": "Coin",
                    "Amount": "",
                    "Value in CAD": "100",
                }
            ],
        )


def test_parse_baseline_export_rows_rejects_non_positive_duplicate_counts() -> None:
    with pytest.raises(ValidationError, match="duplicate_count must be positive"):
        parse_baseline_export_rows(
            "Duplicate Transactions",
            [
                {
                    "# of duplicates": "0",
                    "Type": "Trade",
                    "Exchange": "Fixture",
                    "Exchange ID": "fixture",
                    "Buy": "1 BTC",
                    "Sell": "10 CAD",
                    "Trade Group": "",
                    "Tx ID": "tx-1",
                    "Tx Date": "2023-08-05 08:34:04",
                }
            ],
        )
