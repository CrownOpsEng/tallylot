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

    assert rows.trade_rows == [
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
        }
    ]
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
