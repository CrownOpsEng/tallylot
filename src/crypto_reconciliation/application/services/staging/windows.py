"""Normalization-window helpers for staging workflows."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import cast

from crypto_reconciliation.application.services.export_files import find_required_csv_export
from crypto_reconciliation.domain.value_objects import parse_timestamp

from .validation import read_candidate_rows

DEFAULT_NORMALIZATION_WINDOW_END = "2025-12-31 23:59:59"


def resolve_normalization_window(
    *,
    candidate: Path,
    baseline_export_dir: Path,
    normalization_summary: Path | None,
    window_start: str | None,
    window_end: str | None,
) -> tuple[str, str, str]:
    baseline_trade_table = find_required_csv_export(baseline_export_dir, "Trade Table")
    baseline_rows = read_candidate_rows(baseline_trade_table)
    baseline_cutoff = max(parse_timestamp(row["Date"]) for row in baseline_rows if row.get("Date"))
    effective_window_start = (
        window_start
        if window_start is not None
        else (baseline_cutoff + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
    )
    effective_window_end = DEFAULT_NORMALIZATION_WINDOW_END if window_end is None else window_end
    summary_path = normalization_summary
    if summary_path is None:
        sibling_path = candidate.parent / "normalization_summary.json"
        if sibling_path.exists():
            summary_path = sibling_path
    if summary_path is None:
        return effective_window_start, effective_window_end, ""
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Normalization summary must be a JSON object: {summary_path}")
    typed_payload = cast(dict[str, object], payload)
    if window_start is None:
        summary_start = typed_payload.get("normalization_window_start")
        if isinstance(summary_start, str) and summary_start:
            effective_window_start = summary_start
    if window_end is None:
        summary_end = typed_payload.get("normalization_window_end")
        if isinstance(summary_end, str) and summary_end:
            effective_window_end = summary_end
    return effective_window_start, effective_window_end, str(summary_path.resolve())


def count_candidate_rows_outside_window(
    candidate_path: Path,
    *,
    window_start: str,
    window_end: str,
) -> int:
    start_dt = parse_timestamp(window_start)
    end_dt = parse_timestamp(window_end)
    rows_outside_window = 0
    for row in read_candidate_rows(candidate_path):
        date_value = (row.get("Date") or "").strip()
        if not date_value:
            continue
        date_dt = parse_timestamp(date_value)
        if date_dt < start_dt or date_dt > end_dt:
            rows_outside_window += 1
    return rows_outside_window
