from __future__ import annotations

from tallylot.adapters.support import (
    TimezoneReviewPolicy,
    passed_timezone_summary,
    reviewed_timezone_summary,
)
from tallylot.ports.source_profiles import FileInventoryEntry
from tests.support.services import build_source_profile


def test_passed_timezone_summary_rejects_conflicting_profile_timezone_metadata() -> (
    None
):
    profile = build_source_profile(
        adapter_id="coinbase",
        source="coinbase",
        file_inventory=(
            FileInventoryEntry(
                relative_path="retail-export.csv",
                suffix=".csv",
                size_bytes=1,
                sha256="fixture",
                family="coinbase:retail_export",
                date_field="Timestamp",
                timezone_mode="conflict",
                timezone_value="UTC",
                timezone_conflict="header:Timestamp (UTC)|value:2026-03-23 15:47:00-06:00",
            ),
        ),
    )

    summary, issues = passed_timezone_summary(profile, mode="value_utc")

    assert summary["status"] == "needs_review"
    assert summary["issue_count"] == 1
    assert [issue.kind for issue in issues] == ["timezone_conflict_detected"]


def test_passed_timezone_summary_detects_overlapping_timezone_shift_risk() -> None:
    profile = build_source_profile(
        adapter_id="binance",
        source="Binance",
        file_inventory=(
            FileInventoryEntry(
                relative_path="spot-utc-6.csv",
                suffix=".csv",
                size_bytes=1,
                sha256="a",
                family="binance:spot_trade_history",
                date_field="Time",
                min_timestamp="2026-03-23 10:00:00",
                max_timestamp="2026-03-23 11:00:00",
                timezone_mode="filename_offset",
                timezone_value="UTC-06:00",
            ),
            FileInventoryEntry(
                relative_path="spot-utc-5.csv",
                suffix=".csv",
                size_bytes=1,
                sha256="b",
                family="binance:spot_trade_history",
                date_field="Time",
                min_timestamp="2026-03-23 10:30:00",
                max_timestamp="2026-03-23 11:30:00",
                timezone_mode="filename_offset",
                timezone_value="UTC-05:00",
            ),
        ),
    )

    summary, issues = passed_timezone_summary(profile, mode="filename_offset")

    assert summary["status"] == "needs_review"
    assert summary["issue_count"] == 1
    assert [issue.kind for issue in issues] == [
        "timezone_shift_overlap_review_required"
    ]


def test_passed_timezone_summary_ignores_local_overlap_without_utc_overlap() -> None:
    profile = build_source_profile(
        adapter_id="binance",
        source="Binance",
        file_inventory=(
            FileInventoryEntry(
                relative_path="spot-west.csv",
                suffix=".csv",
                size_bytes=1,
                sha256="a",
                family="binance:spot_trade_history",
                date_field="Time",
                min_timestamp="2026-03-23 10:00:00",
                max_timestamp="2026-03-23 11:00:00",
                timezone_mode="filename_offset",
                timezone_value="UTC-12:00",
            ),
            FileInventoryEntry(
                relative_path="spot-east.csv",
                suffix=".csv",
                size_bytes=1,
                sha256="b",
                family="binance:spot_trade_history",
                date_field="Time",
                min_timestamp="2026-03-23 10:30:00",
                max_timestamp="2026-03-23 11:30:00",
                timezone_mode="filename_offset",
                timezone_value="UTC+12:00",
            ),
        ),
    )

    summary, issues = passed_timezone_summary(profile, mode="filename_offset")

    assert summary["status"] == "passed"
    assert summary["issue_count"] == 0
    assert not issues


def test_reviewed_timezone_summary_accepts_explicit_filename_offsets() -> None:
    profile = build_source_profile(
        adapter_id="binance",
        source="Binance",
        file_inventory=(
            FileInventoryEntry(
                relative_path="dated.csv",
                suffix=".csv",
                size_bytes=1,
                sha256="fixture",
                family="binance:spot_trade_history",
                date_field="Time",
                min_timestamp="2026-03-23 10:00:00",
                max_timestamp="2026-03-23 11:00:00",
                timezone_mode="filename_offset",
                timezone_value="UTC-06:00",
            ),
        ),
    )

    summary, issues = reviewed_timezone_summary(
        profile,
        policy=TimezoneReviewPolicy(
            adapter_id="binance",
            mode="naive",
            message="Binance exports with dated rows must include a filename offset before normalization.",
            accepted_modes=frozenset({"filename_offset"}),
        ),
    )

    assert summary["status"] == "passed"
    assert summary["issue_count"] == 0
    assert summary["mode_counts"] == {"filename_offset": 1}
    assert not issues


def test_passed_timezone_summary_accepts_shakepay_local_wall_clock_exports() -> None:
    profile = build_source_profile(
        adapter_id="shakepay",
        source="Shakepay",
        file_inventory=(
            FileInventoryEntry(
                relative_path="cash_transactions_summary.csv",
                suffix=".csv",
                size_bytes=1,
                sha256="fixture",
                family="shakepay:cash_summary",
                date_field="Date",
                min_timestamp="2024-01-01 14:10:11",
                max_timestamp="2024-01-03 13:00:00",
                timezone_mode="naive",
            ),
        ),
    )

    summary, issues = passed_timezone_summary(profile, mode="america_toronto")

    assert summary["status"] == "passed"
    assert summary["issue_count"] == 0
    assert summary["mode_counts"] == {"naive": 1}
    assert not issues
