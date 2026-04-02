"""CoinTracking overlap detection helpers."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from tallylot.domain.types import JsonValue
from tools.oracles.contracts import OverlapResult

from .screening_columns import (
    cell,
    load_cointracking_rows,
    overlap_signature,
)

DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S")
OVERLAP_FLAGGED_HEADER = (
    "row_number",
    "reasons",
    "type",
    "buy",
    "buy_currency",
    "sell",
    "sell_currency",
    "fee",
    "fee_currency",
    "exchange",
    "date",
    "tx_id",
)


def summarize_candidate_overlap(
    baseline_export_dir: Path,
    candidate_path: Path,
) -> OverlapResult:
    trade_table_path = find_trade_table(baseline_export_dir)
    _, baseline_rows, baseline_columns = load_cointracking_rows(trade_table_path)
    candidate_header, candidate_rows, candidate_columns = load_cointracking_rows(candidate_path)

    baseline_dates = [
        parse_overlap_datetime(cell(row, baseline_columns["date"]))
        for row in baseline_rows
        if cell(row, baseline_columns["date"])
    ]
    if not baseline_dates:
        raise ValueError("Baseline Trade Table did not contain any dated rows")
    cutoff = max(baseline_dates)

    baseline_tx_ids = {
        cell(row, baseline_columns["tx_id"]) for row in baseline_rows if cell(row, baseline_columns["tx_id"])
    }
    baseline_signatures = Counter(overlap_signature(row, baseline_columns) for row in baseline_rows)

    flagged_rows: list[dict[str, str]] = []
    before_or_at_cutoff_rows = 0
    blank_date_rows = 0
    unparsable_date_rows = 0
    baseline_tx_id_matches = 0
    baseline_signature_matches = 0

    for row_number, row in enumerate(candidate_rows, start=2):
        reasons: list[str] = []
        raw_date = cell(row, candidate_columns["date"])
        parsed_date: datetime | None = None
        if not raw_date:
            blank_date_rows += 1
            reasons.append("blank_date")
        else:
            try:
                parsed_date = parse_overlap_datetime(raw_date)
            except ValueError:
                unparsable_date_rows += 1
                reasons.append("unparseable_date")

        if parsed_date is not None and parsed_date <= cutoff:
            before_or_at_cutoff_rows += 1
            reasons.append("on_or_before_cutoff")

        tx_id = cell(row, candidate_columns["tx_id"])
        if tx_id and tx_id in baseline_tx_ids:
            baseline_tx_id_matches += 1
            reasons.append("baseline_tx_id_match")

        signature = overlap_signature(row, candidate_columns)
        if baseline_signatures[signature] > 0:
            baseline_signature_matches += 1
            reasons.append("baseline_economic_signature_match")

        if reasons:
            flagged_rows.append(
                {
                    "row_number": str(row_number),
                    "reasons": ";".join(reasons),
                    "type": cell(row, candidate_columns["type"]),
                    "buy": cell(row, candidate_columns["buy"]),
                    "buy_currency": cell(row, candidate_columns["buy_currency"]),
                    "sell": cell(row, candidate_columns["sell"]),
                    "sell_currency": cell(row, candidate_columns["sell_currency"]),
                    "fee": cell(row, candidate_columns["fee"]),
                    "fee_currency": cell(row, candidate_columns["fee_currency"]),
                    "exchange": cell(row, candidate_columns["exchange"]),
                    "date": raw_date,
                    "tx_id": tx_id,
                }
            )

    summary = cast(
        dict[str, JsonValue],
        {
            "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "baseline_trade_table": str(trade_table_path),
            "candidate_file": str(candidate_path.resolve()),
            "candidate_header_columns": candidate_header,
            "cutoff_timestamp": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
            "candidate_row_count": len(candidate_rows),
            "rows_flagged": len(flagged_rows),
            "rows_on_or_before_cutoff": before_or_at_cutoff_rows,
            "rows_with_blank_date": blank_date_rows,
            "rows_with_unparseable_date": unparsable_date_rows,
            "rows_with_baseline_tx_id_match": baseline_tx_id_matches,
            "rows_with_baseline_economic_signature_match": baseline_signature_matches,
            "status": "pass" if not flagged_rows else "review_required",
        },
    )
    return OverlapResult(summary=summary, flagged_rows=tuple(flagged_rows))


def write_overlap_artifacts(
    output_dir: Path,
    result: OverlapResult,
    *,
    write_json: Callable[[Path, JsonValue], None],
    write_rows: Callable[[Path, tuple[str, ...], Iterable[dict[str, str]]], None],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "overlap_summary.json", result.summary)
    write_rows(output_dir / "overlap_flagged_rows.csv", OVERLAP_FLAGGED_HEADER, result.flagged_rows)


def parse_overlap_datetime(value: str) -> datetime:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    raise ValueError(f"Unsupported timestamp format: {value!r}")


def find_trade_table(export_dir: Path) -> Path:
    matches = sorted(path for path in export_dir.glob("*.csv") if "trade table" in path.name.lower())
    if not matches:
        raise FileNotFoundError(f"Missing required export containing 'Trade Table' in {export_dir}")
    if len(matches) > 1:
        candidates = ", ".join(path.name for path in matches)
        raise ValueError(f"Ambiguous export for 'Trade Table' in {export_dir}: {candidates}")
    return matches[0]
