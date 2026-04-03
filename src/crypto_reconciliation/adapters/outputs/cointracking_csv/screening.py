"""CoinTracking-specific candidate screening."""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from crypto_reconciliation.domain.models import IssueRecord
from crypto_reconciliation.domain.types import JsonValue
from crypto_reconciliation.domain.value_objects import parse_timestamp
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.output_workflows import OverlapResult, ScreeningResult

from .schema import COINTRACKING_HEADER

DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S")
TX_ID_HEADERS = ("Tx-ID", "Tx ID", "Trade ID", "Transaction ID")
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


def match_candidate(candidate_path: Path, artifacts: ArtifactStorePort) -> int:
    try:
        header = tuple(artifacts.read_rows(candidate_path)[0].keys())
    except (FileNotFoundError, IndexError, KeyError):
        return 0
    return 100 if header == COINTRACKING_HEADER else 0


def screen_candidate(
    candidate_path: Path,
    baseline_export_dir: Path,
    artifacts: ArtifactStorePort,
) -> ScreeningResult:
    baseline_trade_table = _find_trade_table(baseline_export_dir)
    baseline_rows = artifacts.read_rows(baseline_trade_table)
    baseline_cutoff = max(parse_timestamp(row["Date"]) for row in baseline_rows if row.get("Date"))
    baseline_tx_ids = {row.get("Tx-ID", "") for row in baseline_rows if row.get("Tx-ID")}

    issues, candidate_rows, valid_rows = candidate_validation_issues(candidate_path)
    duplicate_count = sum(1 for row in valid_rows if row["Tx-ID"] in baseline_tx_ids)
    has_time_overlap = any(parse_timestamp(row["Date"]) <= baseline_cutoff for row in valid_rows)
    overlap_result = None if issues else summarize_candidate_overlap(baseline_export_dir, candidate_path)
    return ScreeningResult(
        candidate_rows=candidate_rows,
        issues=tuple(issues),
        duplicate_count=duplicate_count,
        has_time_overlap=has_time_overlap,
        overlap_result=overlap_result,
    )


def candidate_validation_issues(candidate_path: Path) -> tuple[list[IssueRecord], int, list[dict[str, str]]]:
    with candidate_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        issues: list[IssueRecord] = []
        if header != COINTRACKING_HEADER:
            issues.append(
                IssueRecord(
                    issue_id=f"{candidate_path.name}:schema",
                    source="batch_screen",
                    adapter_id="cointracking_csv",
                    severity="high",
                    kind="invalid_schema",
                    message="The candidate file does not match the CoinTracking CSV header.",
                    raw_file=candidate_path.name,
                )
            )
            return issues, 0, []

        rows = list(reader)
    valid_rows: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=2):
        date_value = (row.get("Date") or "").strip()
        tx_id = (row.get("Tx-ID") or "").strip()
        if not date_value:
            issues.append(issue(candidate_path, index, "missing_date", "Candidate rows must include Date."))
            continue
        if not tx_id:
            issues.append(issue(candidate_path, index, "missing_tx_id", "Candidate rows must include Tx-ID."))
            continue
        try:
            parse_timestamp(date_value)
        except ValueError:
            issues.append(
                issue(
                    candidate_path,
                    index,
                    "invalid_date",
                    f"Unsupported Date value: {date_value!r}.",
                )
            )
            continue
        valid_rows.append(row)
    return issues, len(rows), valid_rows


def summarize_candidate_overlap(
    baseline_export_dir: Path,
    candidate_path: Path,
) -> OverlapResult:
    trade_table_path = _find_trade_table(baseline_export_dir)
    _, baseline_rows, baseline_columns = _load_cointracking_rows(trade_table_path)
    candidate_header, candidate_rows, candidate_columns = _load_cointracking_rows(candidate_path)

    baseline_dates = [
        parse_overlap_datetime(_cell(row, baseline_columns["date"]))
        for row in baseline_rows
        if _cell(row, baseline_columns["date"])
    ]
    if not baseline_dates:
        raise ValueError("Baseline Trade Table did not contain any dated rows")
    cutoff = max(baseline_dates)

    baseline_tx_ids = {
        _cell(row, baseline_columns["tx_id"]) for row in baseline_rows if _cell(row, baseline_columns["tx_id"])
    }
    baseline_signatures = Counter(_overlap_signature(row, baseline_columns) for row in baseline_rows)

    flagged_rows: list[dict[str, str]] = []
    before_or_at_cutoff_rows = 0
    blank_date_rows = 0
    unparsable_date_rows = 0
    baseline_tx_id_matches = 0
    baseline_signature_matches = 0

    for row_number, row in enumerate(candidate_rows, start=2):
        reasons: list[str] = []
        raw_date = _cell(row, candidate_columns["date"])
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

        tx_id = _cell(row, candidate_columns["tx_id"])
        if tx_id and tx_id in baseline_tx_ids:
            baseline_tx_id_matches += 1
            reasons.append("baseline_tx_id_match")

        signature = _overlap_signature(row, candidate_columns)
        if baseline_signatures[signature] > 0:
            baseline_signature_matches += 1
            reasons.append("baseline_economic_signature_match")

        if reasons:
            flagged_rows.append(
                {
                    "row_number": str(row_number),
                    "reasons": ";".join(reasons),
                    "type": _cell(row, candidate_columns["type"]),
                    "buy": _cell(row, candidate_columns["buy"]),
                    "buy_currency": _cell(row, candidate_columns["buy_currency"]),
                    "sell": _cell(row, candidate_columns["sell"]),
                    "sell_currency": _cell(row, candidate_columns["sell_currency"]),
                    "fee": _cell(row, candidate_columns["fee"]),
                    "fee_currency": _cell(row, candidate_columns["fee_currency"]),
                    "exchange": _cell(row, candidate_columns["exchange"]),
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


def issue(candidate_path: Path, row_ref: int, kind: str, message: str) -> IssueRecord:
    return IssueRecord(
        issue_id=f"{candidate_path.name}:{row_ref}:{kind}",
        source="batch_screen",
        adapter_id="cointracking_csv",
        severity="high",
        kind=kind,
        message=message,
        raw_file=candidate_path.name,
        raw_row_ref=str(row_ref),
    )


def _find_trade_table(export_dir: Path) -> Path:
    matches = sorted(path for path in export_dir.glob("*.csv") if "trade table" in path.name.lower())
    if not matches:
        raise FileNotFoundError(f"Missing required export containing 'Trade Table' in {export_dir}")
    if len(matches) > 1:
        candidates = ", ".join(path.name for path in matches)
        raise ValueError(f"Ambiguous export for 'Trade Table' in {export_dir}: {candidates}")
    return matches[0]


def _load_cointracking_rows(path: Path) -> tuple[list[str], list[list[str]], dict[str, int | None]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None:
            raise ValueError(f"CSV file is empty: {path}")
        rows = [row for row in reader if any(cell.strip() for cell in row)]
    columns = _build_cointracking_column_map(header)
    return header, rows, columns


def _build_cointracking_column_map(header: list[str]) -> dict[str, int | None]:
    type_index = _find_header_index(header, "Type")
    buy_index = _find_header_index(header, "Buy")
    sell_index = _find_header_index(header, "Sell")
    fee_index = _find_header_index(header, "Fee")
    buy_currency_index = _find_next_header_index(header, "Cur.", buy_index) if buy_index is not None else None
    sell_currency_index = _find_next_header_index(header, "Cur.", sell_index) if sell_index is not None else None
    fee_currency_index = _find_next_header_index(header, "Cur.", fee_index) if fee_index is not None else None
    date_index = _find_header_index(header, "Date")
    if date_index is None:
        date_index = _find_header_index(header, "Trade Date")
    exchange_index = _find_header_index(header, "Exchange")
    group_index = _find_header_index(header, "Group")
    if group_index is None:
        group_index = _find_header_index(header, "Trade Group")
    comment_index = _find_header_index(header, "Comment")

    tx_id_index = None
    for header_name in TX_ID_HEADERS:
        tx_id_index = _find_header_index(header, header_name)
        if tx_id_index is not None:
            break

    if type_index is None or date_index is None:
        raise ValueError("Candidate file must contain at least 'Type' and 'Date' or 'Trade Date' columns")

    return {
        "type": type_index,
        "buy": buy_index,
        "buy_currency": buy_currency_index,
        "sell": sell_index,
        "sell_currency": sell_currency_index,
        "fee": fee_index,
        "fee_currency": fee_currency_index,
        "exchange": exchange_index,
        "group": group_index,
        "comment": comment_index,
        "date": date_index,
        "tx_id": tx_id_index,
    }


def _find_header_index(header: list[str], name: str) -> int | None:
    try:
        return header.index(name)
    except ValueError:
        return None


def _find_next_header_index(header: list[str], name: str, start: int) -> int | None:
    for index in range(start + 1, len(header)):
        if header[index] == name:
            return index
    return None


def _cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def _overlap_signature(row: list[str], columns: dict[str, int | None]) -> tuple[str, ...]:
    return (
        _cell(row, columns["type"]),
        _cell(row, columns["buy"]),
        _cell(row, columns["buy_currency"]),
        _cell(row, columns["sell"]),
        _cell(row, columns["sell_currency"]),
        _cell(row, columns["fee"]),
        _cell(row, columns["fee_currency"]),
        _cell(row, columns["exchange"]),
        _cell(row, columns["date"]),
    )
