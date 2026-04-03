#!/usr/bin/env python3

"""Shared overlap detection for raw evidence and CoinTracking candidates."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from pipeline_common import CANONICAL_BASELINE_REQUIRED_FILES
from script_common import find_required_csv_exports, require_directory, sha256sum, write_csv_rows, write_json


TRADE_TABLE_MARKER = "Trade Table"
DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S")
TX_ID_HEADERS = ("Tx-ID", "Tx ID", "Trade ID", "Transaction ID")


@dataclass(frozen=True)
class ManifestHit:
    manifest_path: Path
    capture_dir: Path
    filename: str

def load_manifest_index(root: Path) -> dict[str, list[ManifestHit]]:
    index: dict[str, list[ManifestHit]] = defaultdict(list)
    for manifest_path in sorted(root.rglob("manifest.csv")):
        with manifest_path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                index[row.get("sha256", "")].append(
                    ManifestHit(
                        manifest_path=manifest_path,
                        capture_dir=manifest_path.parent,
                        filename=row.get("filename", ""),
                    )
                )
    return index


def summarize_file_overlap(paths: Iterable[Path], *, repo_root: Path) -> tuple[dict[str, object], list[dict[str, str]]]:
    resolved_paths = [path.resolve() for path in paths]
    manifest_index = load_manifest_index(repo_root / "01_raw_exports")
    seen_hashes: dict[str, Path] = {}
    rows: list[dict[str, str]] = []
    repo_hits = 0
    internal_hits = 0
    for path in sorted(resolved_paths):
        digest = sha256sum(path)
        internal_match = seen_hashes.get(digest)
        repo_matches = manifest_index.get(digest, [])
        reasons: list[str] = []
        if internal_match is not None:
            internal_hits += 1
            reasons.append("incoming_duplicate")
        if repo_matches:
            repo_hits += 1
            reasons.append("repo_manifest_match")
        if reasons:
            rows.append(
                {
                    "path": str(path),
                    "sha256": digest,
                    "reasons": ";".join(reasons),
                    "incoming_match": str(internal_match) if internal_match is not None else "",
                    "repo_matches": "; ".join(f"{hit.capture_dir}/{hit.filename}" for hit in repo_matches),
                }
            )
        seen_hashes.setdefault(digest, path)
    return (
        {
            "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "file_count": len(resolved_paths),
            "internal_duplicate_hits": internal_hits,
            "repo_manifest_hits": repo_hits,
        },
        rows,
    )


def find_trade_table(export_dir: Path) -> Path:
    export_dir = require_directory(export_dir.resolve(), "Baseline export directory")
    return find_required_csv_exports(
        export_dir,
        {"trade_table": TRADE_TABLE_MARKER},
        "Baseline export directory",
    )["trade_table"]


def parse_overlap_datetime(value: str) -> datetime:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported timestamp format: {value!r}")


def find_header_index(header: list[str], name: str) -> int | None:
    try:
        return header.index(name)
    except ValueError:
        return None


def find_next_header_index(header: list[str], name: str, start: int) -> int | None:
    for index in range(start + 1, len(header)):
        if header[index] == name:
            return index
    return None


def build_cointracking_column_map(header: list[str]) -> dict[str, int | None]:
    type_index = find_header_index(header, "Type")
    buy_index = find_header_index(header, "Buy")
    sell_index = find_header_index(header, "Sell")
    fee_index = find_header_index(header, "Fee")
    buy_currency_index = find_next_header_index(header, "Cur.", buy_index) if buy_index is not None else None
    sell_currency_index = find_next_header_index(header, "Cur.", sell_index) if sell_index is not None else None
    fee_currency_index = find_next_header_index(header, "Cur.", fee_index) if fee_index is not None else None
    date_index = find_header_index(header, "Date")
    if date_index is None:
        date_index = find_header_index(header, "Trade Date")
    exchange_index = find_header_index(header, "Exchange")
    group_index = find_header_index(header, "Group")
    if group_index is None:
        group_index = find_header_index(header, "Trade Group")
    comment_index = find_header_index(header, "Comment")

    tx_id_index = None
    for header_name in TX_ID_HEADERS:
        tx_id_index = find_header_index(header, header_name)
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


def cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def build_overlap_signature(row: list[str], columns: dict[str, int | None]) -> tuple[str, ...]:
    return (
        cell(row, columns["type"]),
        cell(row, columns["buy"]),
        cell(row, columns["buy_currency"]),
        cell(row, columns["sell"]),
        cell(row, columns["sell_currency"]),
        cell(row, columns["fee"]),
        cell(row, columns["fee_currency"]),
        cell(row, columns["exchange"]),
        cell(row, columns["date"]),
    )


def load_cointracking_rows(path: Path) -> tuple[list[str], list[list[str]], dict[str, int | None]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None:
            raise ValueError(f"CSV file is empty: {path}")
        rows = [row for row in reader]
    columns = build_cointracking_column_map(header)
    return header, rows, columns


def summarize_candidate_overlap(
    baseline_export_dir: Path,
    candidate_path: Path,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    trade_table_path = find_trade_table(baseline_export_dir)
    _, baseline_rows, baseline_columns = load_cointracking_rows(trade_table_path)
    candidate_header, candidate_rows, candidate_columns = load_cointracking_rows(candidate_path.resolve())

    baseline_dates = [parse_overlap_datetime(cell(row, baseline_columns["date"])) for row in baseline_rows if cell(row, baseline_columns["date"])]
    if not baseline_dates:
        raise ValueError("Baseline Trade Table did not contain any dated rows")
    cutoff = max(baseline_dates)

    baseline_tx_ids = {
        cell(row, baseline_columns["tx_id"])
        for row in baseline_rows
        if cell(row, baseline_columns["tx_id"])
    }
    baseline_signatures = Counter(build_overlap_signature(row, baseline_columns) for row in baseline_rows)

    flagged_rows: list[dict[str, str]] = []
    before_or_at_cutoff_rows = 0
    blank_date_rows = 0
    unparsable_date_rows = 0
    baseline_tx_id_matches = 0
    baseline_exact_matches = 0

    for row_number, row in enumerate(candidate_rows, start=2):
        reasons: list[str] = []
        raw_date = cell(row, candidate_columns["date"])
        parsed_date = None
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

        signature = build_overlap_signature(row, candidate_columns)
        if baseline_signatures[signature] > 0:
            baseline_exact_matches += 1
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

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
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
        "rows_with_baseline_economic_signature_match": baseline_exact_matches,
        "status": "pass" if not flagged_rows else "review_required",
    }
    return summary, flagged_rows


def write_candidate_overlap_artifacts(out_dir: Path, summary: dict[str, object], flagged_rows: list[dict[str, str]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "overlap_summary.json", summary)
    write_csv_rows(
        out_dir / "overlap_flagged_rows.csv",
        [
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
        ],
        flagged_rows,
    )
