"""CoinTracking-specific candidate screening."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.domain.value_objects import parse_timestamp
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.output_workflows import ScreeningResult

from .screening_columns import build_cointracking_column_map as _build_cointracking_column_map
from .screening_overlap import (
    find_trade_table,
    parse_overlap_datetime,
    summarize_candidate_overlap,
    write_overlap_artifacts,
)
from .screening_validation import candidate_validation_issues, issue, match_candidate

__all__ = [
    "_build_cointracking_column_map",
    "_find_trade_table",
    "candidate_validation_issues",
    "issue",
    "match_candidate",
    "parse_overlap_datetime",
    "screen_candidate",
    "summarize_candidate_overlap",
    "write_overlap_artifacts",
]


def screen_candidate(
    candidate_path: Path,
    baseline_export_dir: Path,
    artifacts: ArtifactStorePort,
) -> ScreeningResult:
    baseline_trade_table = find_trade_table(baseline_export_dir)
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


_find_trade_table = find_trade_table
