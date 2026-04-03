from __future__ import annotations

from pathlib import Path

import pytest

from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tools.oracles.cointracking.baseline import find_required_baseline_exports
from tools.oracles.cointracking.baseline.rows import (
    parse_baseline_export_rows,
    read_baseline_export_rows,
)


def test_parse_baseline_export_rows_normalizes_cointracking_day_first_timestamps() -> (
    None
):
    rows = parse_baseline_export_rows(
        "Missing Transactions",
        [
            {
                "Type": "Deposit",
                "Amount": "1.5",
                "Cur.": "BTC",
                "Fee": "",
                "Fee Cur.": "",
                "Value in CAD": "100",
                "Exchange": "Fixture",
                "Trade Group": "",
                "Comment": "",
                "Trade ID": "m-1",
                "Date": "14.07.2022 20:42:32",
                "Match": "",
            }
        ],
    )

    assert rows[0]["Date"] == "2022-07-14 20:42:32"


def test_read_baseline_export_rows_parses_duplicate_trade_currency_headers(
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    (export_dir / "Trade Table.csv").write_text(
        (
            "Type,Buy,Cur.,Sell,Cur.,Fee,Cur.,Exchange,Group,Comment,Date,LPN,Tx-ID\n"
            "Trade,0.00175640,BTC,25.00000000,CAD,1.49000000,CAD,Coinbase,,"
            '"Bought 0.0017564 BTC for $25.00 CAD",2019-09-11 01:06:26,,tx-1\n'
        ),
        encoding="utf-8",
    )
    for stem, header in (
        ("Current Balance", "Ticker,Name,Type,Amount,Value in CAD\n"),
        (
            "Balance by Exchange",
            "Amount,Currency,Current value in CAD,Current value in BTC,Exchange\n",
        ),
        ("Validate Transactions", "Issue\n"),
        (
            "Missing Transactions",
            "Type,Amount,Cur.,Fee,Fee Cur.,Value in CAD,Exchange,Trade Group,Comment,Trade ID,Date,Match\n",
        ),
        (
            "Duplicate Transactions",
            "# of duplicates,Type,Exchange,Exchange ID,Buy,Sell,Trade Group,Tx ID,Tx Date\n",
        ),
    ):
        (export_dir / f"{stem}.csv").write_text(header, encoding="utf-8")

    rows = read_baseline_export_rows(
        find_required_baseline_exports(export_dir),
        FilesystemArtifactStore(),
    )

    assert rows.trade_rows == (
        {
            "Type": "Trade",
            "Buy": "0.00175640",
            "Cur.": "BTC",
            "Sell": "25.00000000",
            "Cur..1": "CAD",
            "Fee": "1.49000000",
            "Cur..2": "CAD",
            "Exchange": "Coinbase",
            "Group": "",
            "Comment": "Bought 0.0017564 BTC for $25.00 CAD",
            "Date": "2019-09-11 01:06:26",
            "Tx-ID": "tx-1",
        },
    )


def test_read_baseline_export_rows_rejects_non_blank_trade_lpn_values(
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    (export_dir / "Trade Table.csv").write_text(
        (
            "Type,Buy,Cur.,Sell,Cur.,Fee,Cur.,Exchange,Group,Comment,Date,LPN,Tx-ID\n"
            "Trade,1.0,BTC,10.0,CAD,0.1,CAD,Fixture,,,2023-08-05 08:34:04,1,tx-1\n"
        ),
        encoding="utf-8",
    )
    for stem, header in (
        ("Current Balance", "Ticker,Name,Type,Amount,Value in CAD\n"),
        (
            "Balance by Exchange",
            "Amount,Currency,Current value in CAD,Current value in BTC,Exchange\n",
        ),
        ("Validate Transactions", "Issue\n"),
        (
            "Missing Transactions",
            "Type,Amount,Cur.,Fee,Fee Cur.,Value in CAD,Exchange,Trade Group,Comment,Trade ID,Date,Match\n",
        ),
        (
            "Duplicate Transactions",
            "# of duplicates,Type,Exchange,Exchange ID,Buy,Sell,Trade Group,Tx ID,Tx Date\n",
        ),
    ):
        (export_dir / f"{stem}.csv").write_text(header, encoding="utf-8")

    with pytest.raises(
        ValueError, match="Unsupported non-blank CoinTracking Trade Table LPN value"
    ):
        read_baseline_export_rows(
            find_required_baseline_exports(export_dir),
            FilesystemArtifactStore(),
        )


def test_read_baseline_export_rows_accepts_current_balance_extra_analytics(
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    (export_dir / "Trade Table.csv").write_text(
        "Type,Buy,Cur.,Sell,Cur..1,Fee,Cur..2,Exchange,Group,Comment,Date,Tx-ID\n",
        encoding="utf-8",
    )
    (export_dir / "Current Balance.csv").write_text(
        (
            "Ticker,Name,Type,Amount,Value in CAD,Value in BTC,% of total,Price in BTC,Price in CAD,"
            "Trend 1h in %,Trend 24h in %,Trend 7d in %,Trend 30d in %\n"
            "AGIX,SingularityNET,Coin,4000.00000000,502.59,0.00534165,22.39,0.000001335414,"
            "0.12564812,-0.62,-6.17,6.07,25.19\n"
        ),
        encoding="utf-8",
    )
    for stem, header in (
        (
            "Balance by Exchange",
            "Amount,Currency,Current value in CAD,Current value in BTC,Exchange\n",
        ),
        (
            "Validate Transactions",
            "Urgency,Type,Buy,Cur.,Sell,Cur.,Fee,Exchange,Trade Group,Comment,Trade Date\n",
        ),
        (
            "Missing Transactions",
            "Type,Amount,Cur.,Fee,Fee Cur.,Value in CAD,Exchange,Trade Group,Comment,Trade ID,Date,Match\n",
        ),
        (
            "Duplicate Transactions",
            "# of duplicates,Type,Exchange,Exchange ID,Buy,Sell,Trade Group,Tx ID,Tx Date\n",
        ),
    ):
        (export_dir / f"{stem}.csv").write_text(header, encoding="utf-8")

    rows = read_baseline_export_rows(
        find_required_baseline_exports(export_dir),
        FilesystemArtifactStore(),
    )

    assert rows.current_rows == (
        {
            "Ticker": "AGIX",
            "Name": "SingularityNET",
            "Type": "Coin",
            "Amount": "4000.00000000",
            "Value in CAD": "502.59",
        },
    )


def test_read_baseline_export_rows_normalizes_validate_transaction_exports(
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    (export_dir / "Trade Table.csv").write_text(
        "Type,Buy,Cur.,Sell,Cur..1,Fee,Cur..2,Exchange,Group,Comment,Date,Tx-ID\n",
        encoding="utf-8",
    )
    (export_dir / "Current Balance.csv").write_text(
        "Ticker,Name,Type,Amount,Value in CAD\n",
        encoding="utf-8",
    )
    (export_dir / "Balance by Exchange.csv").write_text(
        "Amount,Currency,Current value in CAD,Current value in BTC,Exchange\n",
        encoding="utf-8",
    )
    (export_dir / "Validate Transactions.csv").write_text(
        (
            "Urgency,Type,Buy,Cur.,Sell,Cur.,Fee,Exchange,Trade Group,Comment,Trade Date\n"
            "Error,Withdrawal,-,,1.92063583,AXS,0.00000000,Ronin - AXS Staking,,,08.02.2023 11:00\n"
        ),
        encoding="utf-8",
    )
    (export_dir / "Missing Transactions.csv").write_text(
        "Type,Amount,Cur.,Fee,Fee Cur.,Value in CAD,Exchange,Trade Group,Comment,Trade ID,Date,Match\n",
        encoding="utf-8",
    )
    (export_dir / "Duplicate Transactions.csv").write_text(
        "# of duplicates,Type,Exchange,Exchange ID,Buy,Sell,Trade Group,Tx ID,Tx Date\n",
        encoding="utf-8",
    )

    rows = read_baseline_export_rows(
        find_required_baseline_exports(export_dir),
        FilesystemArtifactStore(),
    )

    assert rows.validate_rows == (
        {
            "Issue": "Error | Withdrawal | Ronin - AXS Staking | 08.02.2023 11:00",
        },
    )
