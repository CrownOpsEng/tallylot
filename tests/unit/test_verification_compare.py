from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import pytest

import verification_compare
from tests.support.helpers import read_dict_rows, write_csv


def write_verification_set(
    directory: Path,
    *,
    validate_rows: list[list[str]],
    missing_rows: list[list[str]],
    duplicate_rows: list[list[str]],
    current_balance_rows: list[list[str]],
    exchange_rows: list[list[str]],
) -> None:
    write_csv(directory / "Validate Transactions.csv", ["Issue"], validate_rows)
    write_csv(
        directory / "Missing Transactions.csv",
        ["Type", "Amount", "Cur.", "Fee", "Fee Cur.", "Value in CAD", "Exchange", "Trade Group", "Comment", "Trade ID", "Date", "Match", ""],
        missing_rows,
    )
    write_csv(
        directory / "Duplicate Transactions.csv",
        ["", "# of duplicates", "Type", "Exchange", "Exchange ID", "Buy", "Sell", "Trade Group", "Tx ID", "Tx Date"],
        duplicate_rows,
    )
    write_csv(
        directory / "Current Balance.csv",
        ["Ticker", "Name", "Type", "Amount", "Value in CAD"],
        current_balance_rows,
    )
    write_csv(
        directory / "Balance by Exchange.csv",
        ["Amount", "Currency", "Current value in CAD", "Current value in BTC", "Exchange"],
        exchange_rows,
    )


def test_find_required_files_rejects_missing_export(tmp_path: Path) -> None:
    export_dir = tmp_path
    write_csv(export_dir / "Validate Transactions.csv", ["Issue"], [])

    with pytest.raises(FileNotFoundError, match="Missing Transactions"):
        verification_compare.find_required_files(export_dir)


def test_find_required_files_rejects_ambiguous_export(tmp_path: Path) -> None:
    export_dir = tmp_path
    write_csv(export_dir / "a Validate Transactions.csv", ["Issue"], [])
    write_csv(export_dir / "b Validate Transactions.csv", ["Issue"], [])
    for marker in ["Missing Transactions", "Duplicate Transactions", "Current Balance", "Balance by Exchange"]:
        write_csv(export_dir / f"{marker}.csv", ["Issue"], [])

    with pytest.raises(ValueError, match="Ambiguous export"):
        verification_compare.find_required_files(export_dir)


def test_summarize_verification_detects_new_issues_and_balance_changes(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    current_dir = tmp_path / "current"
    reference_dir.mkdir()
    current_dir.mkdir()
    write_verification_set(
        reference_dir,
        validate_rows=[["AXS"]],
        missing_rows=[["Deposit", "1.0", "BTC", "", "", "1.0", "Coinbase", "", "", "trade-1", "2023-08-05 08:34:04", "", ""]],
        duplicate_rows=[],
        current_balance_rows=[["BTC", "Bitcoin", "Coin", "1.00000000", "10.0"], ["CAD", "Canadian Dollar", "Currency", "0.00000000", "0"]],
        exchange_rows=[["1.00000000", "BTC", "10.0", "0.1", "Coinbase"]],
    )
    write_verification_set(
        current_dir,
        validate_rows=[["AXS"], ["NEW"]],
        missing_rows=[["Deposit", "1.0", "BTC", "", "", "1.0", "Coinbase", "", "", "trade-1", "2023-08-05 08:34:04", "", ""]],
        duplicate_rows=[["", "2", "Trade", "Coinbase", "id-1", "1 BTC", "10 CAD", "", "tx-1", "2023-08-05 08:35:00"]],
        current_balance_rows=[["BTC", "Bitcoin", "Coin", "2.50000000", "25.0"], ["CAD", "Canadian Dollar", "Currency", "-5.00000000", "-5"]],
        exchange_rows=[["2.50000000", "BTC", "25.0", "0.2", "Coinbase"], ["-5.00000000", "CAD", "-5.0", "-0.05", "Bank"]],
    )

    summary = verification_compare.summarize_verification(reference_dir, current_dir)

    assert summary["new_validate_rows"] == 1
    assert summary["new_missing_rows"] == 0
    assert summary["current_duplicate_rows"] == 1
    assert summary["current_balance_delta_rows"] == 2
    assert summary["exchange_balance_delta_rows"] == 2
    assert summary["gate_flags"]["has_duplicate_rows"]
    assert summary["gate_flags"]["has_new_validate_rows"]
    assert summary["gate_suggestion"] == "hold"
    assert summary["current_negative_balances"][0]["ticker"] == "CAD"


def test_summarize_verification_detects_resolved_rows_without_new_issues(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    current_dir = tmp_path / "current"
    reference_dir.mkdir()
    current_dir.mkdir()
    write_verification_set(
        reference_dir,
        validate_rows=[["AXS"]],
        missing_rows=[["Deposit", "1.0", "BTC", "", "", "1.0", "Coinbase", "", "", "trade-1", "2023-08-05 08:34:04", "", ""]],
        duplicate_rows=[],
        current_balance_rows=[["BTC", "Bitcoin", "Coin", "1.00000000", "10.0"]],
        exchange_rows=[["1.00000000", "BTC", "10.0", "0.1", "Coinbase"]],
    )
    write_verification_set(
        current_dir,
        validate_rows=[],
        missing_rows=[],
        duplicate_rows=[],
        current_balance_rows=[["BTC", "Bitcoin", "Coin", "1.00000000", "10.0"]],
        exchange_rows=[["1.00000000", "BTC", "10.0", "0.1", "Coinbase"]],
    )

    summary = verification_compare.summarize_verification(reference_dir, current_dir)

    assert summary["new_validate_rows"] == 0
    assert summary["resolved_validate_rows"] == 1
    assert summary["new_missing_rows"] == 0
    assert summary["resolved_missing_rows"] == 1
    assert summary["gate_suggestion"] == "review_balance_changes"


def test_write_verification_artifacts_writes_duplicate_rows_with_dynamic_headers(tmp_path: Path) -> None:
    summary = {
        "new_validate_issue_rows": [],
        "resolved_validate_issue_rows": [],
        "new_missing_transaction_rows": [],
        "resolved_missing_transaction_rows": [],
        "current_balance_deltas": [],
        "exchange_balance_deltas": [],
        "current_duplicate_transaction_rows": [{"Tx ID": "tx-1", "Exchange": "Coinbase"}],
    }

    out_dir = tmp_path
    verification_compare.write_verification_artifacts(out_dir, summary)
    rows = read_dict_rows(out_dir / "current_duplicate_transaction_rows.csv")

    assert rows[0]["Tx ID"] == "tx-1"
    assert rows[0]["Exchange"] == "Coinbase"


def test_write_verification_artifacts_outputs_expected_files(tmp_path: Path) -> None:
    summary = {
        "new_validate_issue_rows": [{"Issue": "NEW"}],
        "resolved_validate_issue_rows": [],
        "new_missing_transaction_rows": [],
        "resolved_missing_transaction_rows": [],
        "current_balance_deltas": [{"ticker": "BTC", "reference_amount": "1.0", "current_amount": "2.0", "difference": "1.0"}],
        "exchange_balance_deltas": [{"exchange": "Coinbase", "currency": "BTC", "reference_amount": "1.0", "current_amount": "2.0", "difference": "1.0"}],
        "current_duplicate_transaction_rows": [],
    }

    out_dir = tmp_path
    verification_compare.write_verification_artifacts(out_dir, summary)

    produced = sorted(path.name for path in out_dir.iterdir())
    new_validate_rows = read_dict_rows(out_dir / "new_validate_issue_rows.csv")

    assert "verification_summary.json" in produced
    assert new_validate_rows[0]["Issue"] == "NEW"


def test_main_prints_summary_json(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    current_dir = tmp_path / "current"
    out_dir = tmp_path / "out"
    reference_dir.mkdir()
    current_dir.mkdir()
    write_verification_set(
        reference_dir,
        validate_rows=[],
        missing_rows=[],
        duplicate_rows=[],
        current_balance_rows=[["BTC", "Bitcoin", "Coin", "1.00000000", "10.0"]],
        exchange_rows=[["1.00000000", "BTC", "10.0", "0.1", "Coinbase"]],
    )
    write_verification_set(
        current_dir,
        validate_rows=[],
        missing_rows=[],
        duplicate_rows=[],
        current_balance_rows=[["BTC", "Bitcoin", "Coin", "1.00000000", "10.0"]],
        exchange_rows=[["1.00000000", "BTC", "10.0", "0.1", "Coinbase"]],
    )

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = verification_compare.main(
            [
                "--reference-dir",
                str(reference_dir),
                "--current-dir",
                str(current_dir),
                "--out-dir",
                str(out_dir),
            ]
        )

    summary = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert summary["gate_suggestion"] == "review_balance_changes"
    assert (out_dir / "verification_summary.json").exists()
