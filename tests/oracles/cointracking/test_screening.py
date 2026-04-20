from __future__ import annotations

import json
from pathlib import Path

import pytest

from tallylot.infrastructure.serialization.csv_io import write_rows
from tallylot.infrastructure.serialization.json_io import write_json
from tools.oracles.cointracking.screening import (
    _build_cointracking_column_map,
    _find_trade_table,
    candidate_validation_issues,
    parse_overlap_datetime,
    summarize_candidate_overlap,
    write_overlap_artifacts,
)
from tools.oracles.contracts import OverlapResult


def test_find_trade_table_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Missing required export"):
        _find_trade_table(tmp_path)


def test_find_trade_table_rejects_ambiguous_file(tmp_path: Path) -> None:
    (tmp_path / "Trade Table A.csv").write_text("x\n", encoding="utf-8")
    (tmp_path / "Trade Table B.csv").write_text("x\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Ambiguous export"):
        _find_trade_table(tmp_path)


def test_parse_overlap_datetime_accepts_both_supported_formats() -> None:
    assert (
        parse_overlap_datetime("2023-08-05 08:34:04").strftime("%Y-%m-%d %H:%M:%S")
        == "2023-08-05 08:34:04"
    )
    assert (
        parse_overlap_datetime("05.08.2023 08:34:04").strftime("%Y-%m-%d %H:%M:%S")
        == "2023-08-05 08:34:04"
    )


def test_build_cointracking_column_map_accepts_alternate_headers() -> None:
    columns = _build_cointracking_column_map(
        [
            "Type",
            "Buy",
            "Cur.",
            "Sell",
            "Cur.",
            "Fee",
            "Cur.",
            "Exchange",
            "Trade Group",
            "Trade Date",
            "Trade ID",
        ]
    )

    assert columns["group"] == 8
    assert columns["date"] == 9
    assert columns["tx_id"] == 10


def test_candidate_validation_accepts_legacy_duplicate_currency_headers(
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "candidate.csv"
    candidate_path.write_text(
        "Type,Buy,Cur.,Sell,Cur.,Fee,Cur.,Exchange,Group,Comment,Date,Tx-ID\n"
        "Trade,1.0,BTC,10.0,CAD,0.1,CAD,Fixture,,ok,2023-08-06 08:34:05,tx-2\n",
        encoding="utf-8",
    )

    issues, candidate_rows, valid_rows = candidate_validation_issues(candidate_path)

    assert not issues
    assert candidate_rows == 1
    assert valid_rows[0]["Cur..1"] == "CAD"
    assert valid_rows[0]["Cur..2"] == "CAD"


def test_build_cointracking_column_map_requires_type_and_date() -> None:
    with pytest.raises(ValueError, match="must contain at least 'Type' and 'Date'"):
        _build_cointracking_column_map(["Buy", "Sell"])


def test_summarize_candidate_overlap_flags_cutoff_and_signature_matches(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "candidate.csv"
    write_rows(
        candidate_path,
        (
            "Type",
            "Buy",
            "Cur.",
            "Sell",
            "Cur..1",
            "Fee",
            "Cur..2",
            "Exchange",
            "Trade Group",
            "Comment",
            "Date",
            "Tx-ID",
        ),
        (
            {
                "Type": "Trade",
                "Buy": "1.0",
                "Cur.": "BTC",
                "Sell": "10.0",
                "Cur..1": "CAD",
                "Fee": "0.1",
                "Cur..2": "CAD",
                "Exchange": "Fixture",
                "Trade Group": "",
                "Comment": "duplicate",
                "Date": "2023-08-05 08:34:04",
                "Tx-ID": "tx-1",
            },
        ),
    )

    result = summarize_candidate_overlap(baseline_export_dir, candidate_path)

    assert result.summary["status"] == "review_required"
    assert result.summary["rows_flagged"] == 1
    assert (
        result.flagged_rows[0]["reasons"]
        == "on_or_before_cutoff;baseline_tx_id_match;baseline_economic_signature_match"
    )


def test_summarize_candidate_overlap_flags_blank_and_unparseable_dates(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "candidate.csv"
    write_rows(
        candidate_path,
        ("Type", "Date"),
        (
            {"Type": "Trade", "Date": ""},
            {"Type": "Trade", "Date": "2023/08/05 08:34:04"},
        ),
    )

    result = summarize_candidate_overlap(baseline_export_dir, candidate_path)

    assert result.summary["rows_with_blank_date"] == 1
    assert result.summary["rows_with_unparseable_date"] == 1
    assert [row["reasons"] for row in result.flagged_rows] == [
        "blank_date",
        "unparseable_date",
    ]


def test_write_overlap_artifacts_writes_summary_and_csv(tmp_path: Path) -> None:
    result = OverlapResult(
        summary={"status": "review_required", "rows_flagged": 1},
        flagged_rows=(
            {
                "row_number": "2",
                "reasons": "duplicate",
                "type": "Trade",
                "buy": "1.0",
                "buy_currency": "BTC",
                "sell": "10.0",
                "sell_currency": "CAD",
                "fee": "0.1",
                "fee_currency": "CAD",
                "exchange": "Fixture",
                "date": "2023-08-05 08:34:04",
                "tx_id": "tx-1",
            },
        ),
    )
    output_dir = tmp_path / "overlap"

    write_overlap_artifacts(
        output_dir, result, write_json=write_json, write_rows=write_rows
    )

    summary = json.loads(
        (output_dir / "overlap_summary.json").read_text(encoding="utf-8")
    )

    assert summary["status"] == "review_required"
    assert (output_dir / "overlap_flagged_rows.csv").exists()
