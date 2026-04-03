from __future__ import annotations

import json
from pathlib import Path

from tallylot.infrastructure.serialization.csv_io import write_rows
from tools.oracles.staging.windows import count_candidate_rows_outside_window, resolve_normalization_window


def test_resolve_normalization_window_uses_baseline_cutoff_plus_one_second(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "candidate.csv"
    candidate_path.write_text("Type,Date\nTrade,2023-08-06 00:00:00\n", encoding="utf-8")

    window_start, window_end, normalization_summary = resolve_normalization_window(
        candidate=candidate_path,
        baseline_export_dir=baseline_export_dir,
        normalization_summary=None,
        window_start=None,
        window_end=None,
    )

    assert window_start == "2023-08-05 08:34:05"
    assert window_end == "2025-12-31 23:59:59"
    assert normalization_summary == ""


def test_resolve_normalization_window_uses_explicit_overrides(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "candidate.csv"
    candidate_path.write_text("Type,Date\nTrade,2023-08-06 00:00:00\n", encoding="utf-8")

    window_start, window_end, _ = resolve_normalization_window(
        candidate=candidate_path,
        baseline_export_dir=baseline_export_dir,
        normalization_summary=None,
        window_start="2024-01-01 00:00:00",
        window_end="2024-12-31 23:59:59",
    )

    assert window_start == "2024-01-01 00:00:00"
    assert window_end == "2024-12-31 23:59:59"


def test_resolve_normalization_window_reads_sibling_summary_when_present(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "candidate.csv"
    candidate_path.write_text("Type,Date\nTrade,2023-08-06 00:00:00\n", encoding="utf-8")
    summary_path = tmp_path / "normalization_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "normalization_window_start": "2024-01-01 00:00:00",
                "normalization_window_end": "2024-12-31 23:59:59",
            }
        ),
        encoding="utf-8",
    )

    window_start, window_end, normalization_summary = resolve_normalization_window(
        candidate=candidate_path,
        baseline_export_dir=baseline_export_dir,
        normalization_summary=None,
        window_start=None,
        window_end=None,
    )

    assert window_start == "2024-01-01 00:00:00"
    assert window_end == "2024-12-31 23:59:59"
    assert normalization_summary.endswith("normalization_summary.json")


def test_count_candidate_rows_outside_window_counts_only_out_of_range_rows(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.csv"
    write_rows(
        candidate_path,
        ("Type", "Date"),
        (
            {"Type": "Trade", "Date": "2024-01-01 00:00:00"},
            {"Type": "Trade", "Date": "2026-01-01 00:00:00"},
            {"Type": "Trade", "Date": ""},
        ),
    )

    assert (
        count_candidate_rows_outside_window(
            candidate_path,
            window_start="2024-01-01 00:00:00",
            window_end="2024-12-31 23:59:59",
        )
        == 1
    )
