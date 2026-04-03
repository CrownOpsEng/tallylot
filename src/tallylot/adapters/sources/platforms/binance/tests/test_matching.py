from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.binance.adapter import _BinanceAdapter
from tallylot.adapters.sources.platforms.binance.csv_rows import is_no_data_row
from tallylot.adapters.sources.platforms.binance.matching import SPOT_HEADER
from tallylot.adapters.sources.platforms.binance.timestamps import parse_export_timestamp
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.ports.source_profiles import FileInventoryEntry
from tests.support.adapter_packs import profile_and_adapter
from tests.support.services import build_source_profile


def test_parse_export_timestamp_applies_binance_filename_offset() -> None:
    parsed = parse_export_timestamp(
        "23-03-23 04:06:00",
        "Binance-Spot-Trade-History-202603230406(UTC--6)_abcd.csv",
    )

    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == "2023-03-23 10:06:00"


def test_parse_export_timestamp_handles_inline_utc_date_without_separator() -> None:
    parsed = parse_export_timestamp("2025-12-31(UTC0)", "Binance.csv")

    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == "2025-12-31 00:00:00"


def test_binance_adapter_matches_known_headers_without_source_label(tmp_path: Path) -> None:
    inventory = (
        FileInventoryEntry(
            relative_path="nested/export.csv",
            suffix=".csv",
            size_bytes=1,
            sha256="abc",
            header=SPOT_HEADER,
        ),
    )

    assert _BinanceAdapter().match("unknown_source", tmp_path, inventory) == 100


def test_binance_adapter_returns_zero_for_unknown_source_without_matching_headers(tmp_path: Path) -> None:
    score = _BinanceAdapter().match(
        "unknown_source",
        tmp_path,
        (
            FileInventoryEntry(
                relative_path="notes.txt",
                suffix=".txt",
                size_bytes=1,
                sha256="abc",
            ),
        ),
    )

    assert score == 0


def test_binance_adapter_reports_timezone_validation_summary_from_inventory() -> None:
    profile = build_source_profile(adapter_id="binance")
    object.__setattr__(
        profile,
        "file_inventory",
        (
            FileInventoryEntry(
                relative_path="dated.csv",
                suffix=".csv",
                size_bytes=1,
                sha256="a",
                date_field="Time",
                timezone_mode="filename_offset",
            ),
            FileInventoryEntry(
                relative_path="undated.csv",
                suffix=".csv",
                size_bytes=1,
                sha256="b",
            ),
        ),
    )

    summary, issues = _BinanceAdapter().validate_profile_timezones(profile)

    assert summary == {
        "status": "passed",
        "issue_count": 0,
        "rows_with_dates": 1,
        "mode_counts": {"filename_offset": 1},
    }
    assert not issues


def test_binance_adapter_extract_location_inventory_is_empty() -> None:
    records, issues = _BinanceAdapter().extract_location_inventory(
        "binance",
        Path("/tmp/raw"),
        build_source_profile(adapter_id="binance"),
    )

    assert not records
    assert not issues


def test_is_no_data_row_detects_binance_sentinel() -> None:
    assert is_no_data_row({"User ID": "No data matches the criteria."})
    assert not is_no_data_row({"User ID": "123"})


def test_binance_translation_uses_family_classification_without_filename_dependency(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "renamed.csv").write_text(
        "Time,Pair,Side,Price,Executed,Amount,Fee\n"
        "23-09-20 18:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n",
        encoding="utf-8",
    )

    profile, adapter = profile_and_adapter("Unknown Exchange", raw_dir)
    result = adapter.translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert str(profile.adapter_id) == "binance"
    assert len(facts) == 1
