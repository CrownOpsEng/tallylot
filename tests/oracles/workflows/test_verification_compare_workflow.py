from __future__ import annotations

import json
from pathlib import Path

from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tests.support.verification import VerificationFixtureSet, write_verification_set
from tools.oracles.contracts import VerificationCompareRequest
from tools.oracles.verification import VerificationCompareService


def test_verification_compare_service_writes_summary(
    verification_previous_dir: Path,
    verification_current_dir: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "verification"

    response = VerificationCompareService(FilesystemArtifactStore()).execute(
        VerificationCompareRequest(
            previous_dir=verification_previous_dir,
            current_dir=verification_current_dir,
            output_dir=output_dir,
        ),
    )

    assert response.changed_reports == 1
    assert (output_dir / "verification_summary.json").exists()


def test_verification_compare_service_detects_new_issues_and_balance_changes(tmp_path: Path) -> None:
    previous_dir = tmp_path / "previous"
    current_dir = tmp_path / "current"
    output_dir = tmp_path / "verification"
    previous_dir.mkdir()
    current_dir.mkdir()
    write_verification_set(
        previous_dir,
        VerificationFixtureSet(
            validate_rows=({"Issue": "AXS"},),
            missing_rows=(
                {
                    "Type": "deposit",
                    "Amount": "1.0",
                    "Cur.": "BTC",
                    "Fee": "",
                    "Fee Cur.": "",
                    "Value in CAD": "1.0",
                    "Exchange": "Coinbase",
                    "Trade Group": "",
                    "Comment": "",
                    "Trade ID": "trade-1",
                    "Date": "2023-08-05 08:34:04",
                    "Match": "",
                    "": "",
                },
            ),
            duplicate_rows=(),
            current_balance_rows=(
                {"Ticker": "BTC", "Name": "Bitcoin", "Type": "Coin", "Amount": "1.00000000", "Value in CAD": "10.0"},
                {
                    "Ticker": "CAD",
                    "Name": "Canadian Dollar",
                    "Type": "Currency",
                    "Amount": "0.00000000",
                    "Value in CAD": "0",
                },
            ),
            exchange_rows=(
                {
                    "Amount": "1.00000000",
                    "Currency": "BTC",
                    "Current value in CAD": "10.0",
                    "Current value in BTC": "0.1",
                    "Exchange": "Coinbase",
                },
            ),
        ),
    )
    write_verification_set(
        current_dir,
        VerificationFixtureSet(
            validate_rows=({"Issue": "AXS"}, {"Issue": "NEW"}),
            missing_rows=(
                {
                    "Type": "deposit",
                    "Amount": "1.0",
                    "Cur.": "BTC",
                    "Fee": "",
                    "Fee Cur.": "",
                    "Value in CAD": "1.0",
                    "Exchange": "Coinbase",
                    "Trade Group": "",
                    "Comment": "",
                    "Trade ID": "trade-1",
                    "Date": "2023-08-05 08:34:04",
                    "Match": "",
                    "": "",
                },
            ),
            duplicate_rows=(
                {
                    "": "",
                    "# of duplicates": "2",
                    "Type": "trade",
                    "Exchange": "Coinbase",
                    "Exchange ID": "id-1",
                    "Buy": "1 BTC",
                    "Sell": "10 CAD",
                    "Trade Group": "",
                    "Tx ID": "tx-1",
                    "Tx Date": "2023-08-05 08:35:00",
                },
            ),
            current_balance_rows=(
                {"Ticker": "BTC", "Name": "Bitcoin", "Type": "Coin", "Amount": "2.50000000", "Value in CAD": "25.0"},
                {
                    "Ticker": "CAD",
                    "Name": "Canadian Dollar",
                    "Type": "Currency",
                    "Amount": "-5.00000000",
                    "Value in CAD": "-5",
                },
            ),
            exchange_rows=(
                {
                    "Amount": "2.50000000",
                    "Currency": "BTC",
                    "Current value in CAD": "25.0",
                    "Current value in BTC": "0.2",
                    "Exchange": "Coinbase",
                },
                {
                    "Amount": "-5.00000000",
                    "Currency": "CAD",
                    "Current value in CAD": "-5.0",
                    "Current value in BTC": "-0.05",
                    "Exchange": "Bank",
                },
            ),
        ),
    )

    response = VerificationCompareService(FilesystemArtifactStore()).execute(
        VerificationCompareRequest(
            previous_dir=previous_dir,
            current_dir=current_dir,
            output_dir=output_dir,
        ),
    )

    summary = json.loads((output_dir / "verification_summary.json").read_text(encoding="utf-8"))
    duplicate_rows = FilesystemArtifactStore().read_rows(output_dir / "current_duplicate_transaction_rows.csv")
    delta_rows = FilesystemArtifactStore().read_rows(output_dir / "current_balance_deltas.csv")

    assert response.changed_reports == 4
    assert response.gate_suggestion == "hold"
    assert summary["new_validate_rows"] == 1
    assert summary["current_duplicate_rows"] == 1
    assert summary["current_negative_balance_rows"] == 1
    assert summary["gate_flags"]["has_duplicate_rows"] is True
    assert duplicate_rows[0]["Tx ID"] == "tx-1"
    assert {row["ticker"] for row in delta_rows} == {"BTC", "CAD"}


def test_verification_compare_service_detects_resolved_rows_without_new_issues(tmp_path: Path) -> None:
    previous_dir = tmp_path / "previous"
    current_dir = tmp_path / "current"
    output_dir = tmp_path / "verification"
    previous_dir.mkdir()
    current_dir.mkdir()
    write_verification_set(
        previous_dir,
        VerificationFixtureSet(
            validate_rows=({"Issue": "AXS"},),
            missing_rows=(
                {
                    "Type": "deposit",
                    "Amount": "1.0",
                    "Cur.": "BTC",
                    "Fee": "",
                    "Fee Cur.": "",
                    "Value in CAD": "1.0",
                    "Exchange": "Coinbase",
                    "Trade Group": "",
                    "Comment": "",
                    "Trade ID": "trade-1",
                    "Date": "2023-08-05 08:34:04",
                    "Match": "",
                    "": "",
                },
            ),
            duplicate_rows=(),
            current_balance_rows=(
                {"Ticker": "BTC", "Name": "Bitcoin", "Type": "Coin", "Amount": "1.00000000", "Value in CAD": "10.0"},
            ),
            exchange_rows=(
                {
                    "Amount": "1.00000000",
                    "Currency": "BTC",
                    "Current value in CAD": "10.0",
                    "Current value in BTC": "0.1",
                    "Exchange": "Coinbase",
                },
            ),
        ),
    )
    write_verification_set(
        current_dir,
        VerificationFixtureSet(
            validate_rows=(),
            missing_rows=(),
            duplicate_rows=(),
            current_balance_rows=(
                {"Ticker": "BTC", "Name": "Bitcoin", "Type": "Coin", "Amount": "1.00000000", "Value in CAD": "10.0"},
            ),
            exchange_rows=(
                {
                    "Amount": "1.00000000",
                    "Currency": "BTC",
                    "Current value in CAD": "10.0",
                    "Current value in BTC": "0.1",
                    "Exchange": "Coinbase",
                },
            ),
        ),
    )

    response = VerificationCompareService(FilesystemArtifactStore()).execute(
        VerificationCompareRequest(
            previous_dir=previous_dir,
            current_dir=current_dir,
            output_dir=output_dir,
        ),
    )

    summary = json.loads((output_dir / "verification_summary.json").read_text(encoding="utf-8"))
    resolved_missing_rows = FilesystemArtifactStore().read_rows(output_dir / "resolved_missing_transaction_rows.csv")

    assert response.changed_reports == 2
    assert response.gate_suggestion == "review_balance_changes"
    assert summary["resolved_validate_rows"] == 1
    assert summary["resolved_missing_rows"] == 1
    assert resolved_missing_rows[0]["Trade ID"] == "trade-1"
