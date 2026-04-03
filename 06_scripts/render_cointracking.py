#!/usr/bin/env python3

"""Render canonical event rows into a CoinTracking-ready candidate CSV."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Sequence

from pipeline_common import CANONICAL_EVENT_HEADERS, validate_canonical_event_row
from script_common import read_csv_rows, write_cointracking_rows, write_json


RENDER_METADATA_HEADERS = (
    "canonical_event_id",
    "confidence",
    "status",
    "raw_file",
    "raw_row_ref",
    "render_match_window_seconds",
    "render_fee_tolerance",
    "render_comment_mode",
    "render_tx_id_mode",
    "render_allowed_types",
    "render_notes",
)


def decimal_text_or_blank(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    return f"{Decimal(text):.8f}"


def render_cointracking_rows(events: Iterable[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    candidate_rows: list[dict[str, str]] = []
    skipped_rows: list[dict[str, str]] = []
    for row in events:
        validate_canonical_event_row(row)
        if row["status"] != "mapped":
            skipped_rows.append(row)
            continue
        candidate_rows.append(
            {
                "Type": row["render_type"] or row["event_kind"],
                "Buy": decimal_text_or_blank(row["amount_in"]),
                "Buy Cur.": row["asset_in"],
                "Sell": decimal_text_or_blank(row["amount_out"]),
                "Sell Cur.": row["asset_out"],
                "Fee": decimal_text_or_blank(row["fee_amount"] or "0"),
                "Fee Cur.": row["fee_asset"],
                "Exchange": row["render_exchange"],
                "Group": row["render_group"],
                "Comment": row["render_comment"] or row["description"],
                "Date": row["timestamp"],
                "Tx-ID": row["render_tx_id"] or row["tx_hash"],
                "canonical_event_id": row["event_id"],
                "confidence": row["confidence"],
                "status": row["status"],
                "raw_file": row["raw_file"],
                "raw_row_ref": row["raw_row_ref"],
                "render_match_window_seconds": row["render_match_window_seconds"],
                "render_fee_tolerance": row["render_fee_tolerance"],
                "render_comment_mode": row["render_comment_mode"],
                "render_tx_id_mode": row["render_tx_id_mode"],
                "render_allowed_types": row["render_allowed_types"],
                "render_notes": row["render_notes"],
            }
        )
    return candidate_rows, skipped_rows


def render_from_file(canonical_events: Path, output: Path, summary_output: Path | None = None) -> dict[str, object]:
    rows = read_csv_rows(canonical_events)
    candidate_rows, skipped_rows = render_cointracking_rows(rows)
    write_cointracking_rows(output, candidate_rows, extra_headers=RENDER_METADATA_HEADERS)
    summary = {
        "canonical_events": len(rows),
        "cointracking_rows": len(candidate_rows),
        "skipped_non_mapped_rows": len(skipped_rows),
        "output": str(output),
    }
    if summary_output is not None:
        write_json(summary_output, summary)
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-events", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary-output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = render_from_file(args.canonical_events, args.output, summary_output=args.summary_output)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

