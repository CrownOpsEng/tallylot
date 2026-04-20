from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tallylot.infrastructure.serialization.csv_io import write_rows


@dataclass(frozen=True)
class VerificationFixtureSet:
    validate_rows: tuple[dict[str, str], ...]
    missing_rows: tuple[dict[str, str], ...]
    duplicate_rows: tuple[dict[str, str], ...]
    current_balance_rows: tuple[dict[str, str], ...]
    exchange_rows: tuple[dict[str, str], ...]


def write_verification_set(
    directory: Path,
    fixture_set: VerificationFixtureSet,
) -> None:
    write_rows(
        directory / "Validate Transactions.csv", ("Issue",), fixture_set.validate_rows
    )
    write_rows(
        directory / "Missing Transactions.csv",
        (
            "Type",
            "Amount",
            "Cur.",
            "Fee",
            "Fee Cur.",
            "Value in CAD",
            "Exchange",
            "Trade Group",
            "Comment",
            "Trade ID",
            "Date",
            "Match",
            "",
        ),
        fixture_set.missing_rows,
    )
    write_rows(
        directory / "Duplicate Transactions.csv",
        (
            "",
            "# of duplicates",
            "Type",
            "Exchange",
            "Exchange ID",
            "Buy",
            "Sell",
            "Trade Group",
            "Tx ID",
            "Tx Date",
        ),
        fixture_set.duplicate_rows,
    )
    write_rows(
        directory / "Current Balance.csv",
        ("Ticker", "Name", "Type", "Amount", "Value in CAD"),
        fixture_set.current_balance_rows,
    )
    write_rows(
        directory / "Balance by Exchange.csv",
        (
            "Amount",
            "Currency",
            "Current value in CAD",
            "Current value in BTC",
            "Exchange",
        ),
        fixture_set.exchange_rows,
    )
