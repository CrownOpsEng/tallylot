from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import pytest

import overlap_check
from tests.support.helpers import read_dict_rows, write_csv


def test_find_trade_table_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Trade Table"):
        overlap_check.find_trade_table(tmp_path)


def test_find_trade_table_rejects_ambiguous_file(tmp_path: Path) -> None:
    export_dir = tmp_path
    write_csv(export_dir / "a Trade Table.csv", ["Type", "Date"], [])
    write_csv(export_dir / "b Trade Table.csv", ["Type", "Date"], [])

    with pytest.raises(ValueError, match="Ambiguous export"):
        overlap_check.find_trade_table(export_dir)


def test_parse_datetime_accepts_both_supported_formats() -> None:
    assert overlap_check.parse_datetime("2023-08-05 08:34:04").strftime("%Y-%m-%d %H:%M:%S") == "2023-08-05 08:34:04"
    assert overlap_check.parse_datetime("05.08.2023 08:34:04").strftime("%Y-%m-%d %H:%M:%S") == "2023-08-05 08:34:04"


def test_build_cointracking_column_map_accepts_alternate_headers() -> None:
    columns = overlap_check.build_cointracking_column_map(
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Trade Group", "Comment", "Trade Date", "Transaction ID"]
    )

    assert columns["group"] is not None
    assert columns["date"] is not None
    assert columns["tx_id"] is not None


def test_build_cointracking_column_map_requires_type_and_date() -> None:
    with pytest.raises(ValueError, match="Type' and 'Date"):
        overlap_check.build_cointracking_column_map(["Buy", "Cur.", "Sell", "Cur."])


def test_summarize_overlap_flags_cutoff_and_signature_matches(tmp_path: Path) -> None:
    export_dir = tmp_path / "baseline"
    export_dir.mkdir()
    candidate = tmp_path / "candidate.csv"
    write_csv(
        export_dir / "Trade Table.csv",
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "LPN", "Tx-ID"],
        [
            ["Trade", "1.0", "BTC", "10.0", "CAD", "0.5", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "", "tx-1"],
            ["Trade", "2.0", "ETH", "20.0", "CAD", "0.1", "CAD", "Coinbase", "", "", "2023-08-05 08:35:04", "", "tx-2"],
        ],
    )
    write_csv(
        candidate,
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
        [
            ["Trade", "1.0", "BTC", "10.0", "CAD", "0.5", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "tx-1"],
            ["Trade", "3.0", "SOL", "30.0", "CAD", "0.2", "CAD", "Coinbase", "", "", "2023-08-05 08:36:04", "tx-3"],
        ],
    )

    summary, flagged_rows = overlap_check.summarize_overlap(export_dir, candidate)

    assert summary["cutoff_timestamp"] == "2023-08-05 08:35:04"
    assert summary["candidate_row_count"] == 2
    assert summary["rows_flagged"] == 1
    assert summary["rows_on_or_before_cutoff"] == 1
    assert summary["rows_with_baseline_tx_id_match"] == 1
    assert summary["rows_with_baseline_economic_signature_match"] == 1
    assert summary["status"] == "review_required"
    assert flagged_rows[0]["row_number"] == "2"
    assert "baseline_tx_id_match" in flagged_rows[0]["reasons"]


def test_summarize_overlap_flags_blank_and_unparseable_dates(tmp_path: Path) -> None:
    export_dir = tmp_path / "baseline"
    export_dir.mkdir()
    candidate = tmp_path / "candidate.csv"
    write_csv(
        export_dir / "Trade Table.csv",
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "LPN", "Tx-ID"],
        [["Trade", "1.0", "BTC", "10.0", "CAD", "0.5", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "", "tx-1"]],
    )
    write_csv(
        candidate,
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
        [
            ["Trade", "2.0", "ETH", "20.0", "CAD", "0.1", "CAD", "Coinbase", "", "", "", "tx-2"],
            ["Trade", "3.0", "SOL", "30.0", "CAD", "0.2", "CAD", "Coinbase", "", "", "2023/08/05 08:35:04", "tx-3"],
        ],
    )

    summary, flagged_rows = overlap_check.summarize_overlap(export_dir, candidate)

    assert summary["rows_flagged"] == 2
    assert summary["rows_with_blank_date"] == 1
    assert summary["rows_with_unparseable_date"] == 1
    assert [row["reasons"] for row in flagged_rows] == ["blank_date", "unparseable_date"]


def test_write_overlap_artifacts_writes_summary_and_csv(tmp_path: Path) -> None:
    summary = {"status": "pass"}
    flagged_rows = [
        {
            "row_number": "2",
            "reasons": "on_or_before_cutoff",
            "type": "Trade",
            "buy": "1",
            "buy_currency": "BTC",
            "sell": "10",
            "sell_currency": "CAD",
            "fee": "0",
            "fee_currency": "CAD",
            "exchange": "Coinbase",
            "date": "2023-08-05 08:34:04",
            "tx_id": "tx-1",
        }
    ]

    out_dir = tmp_path
    overlap_check.write_overlap_artifacts(out_dir, summary, flagged_rows)

    with (out_dir / "overlap_summary.json").open(encoding="utf-8") as handle:
        written_summary = json.load(handle)
    written_rows = read_dict_rows(out_dir / "overlap_flagged_rows.csv")

    assert written_summary["status"] == "pass"
    assert written_rows[0]["tx_id"] == "tx-1"


def test_main_prints_summary_json(tmp_path: Path) -> None:
    export_dir = tmp_path / "baseline"
    export_dir.mkdir()
    candidate = tmp_path / "candidate.csv"
    out_dir = tmp_path / "out"
    write_csv(
        export_dir / "Trade Table.csv",
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "LPN", "Tx-ID"],
        [["Trade", "1.0", "BTC", "10.0", "CAD", "0.5", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "", "tx-1"]],
    )
    write_csv(
        candidate,
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
        [["Trade", "2.0", "ETH", "20.0", "CAD", "0.1", "CAD", "Coinbase", "", "", "2023-08-05 08:35:04", "tx-2"]],
    )

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = overlap_check.main(
            [
                "--baseline-export-dir",
                str(export_dir),
                "--candidate",
                str(candidate),
                "--out-dir",
                str(out_dir),
            ]
        )

    summary = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert summary["status"] == "pass"
    assert (out_dir / "overlap_summary.json").exists()
