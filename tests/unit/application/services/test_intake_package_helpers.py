from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime

from crypto_reconciliation.application.services.intake_package_markers import (
    extract_datetimes,
    logical_key,
    package_cycle_status,
    package_sort_key,
    row_marker,
)
from crypto_reconciliation.application.services.intake_package_models import (
    BundlePackage,
    PlannedPackageItem,
    package_key,
)
from crypto_reconciliation.application.services.intake_package_reviews import (
    apply_default_decisions,
    apply_overlap_review_decisions,
)
from crypto_reconciliation.application.services.intake_package_scope import (
    compatible_scope,
    material_scope_tokens,
    overlap_reason,
    scope_status,
)


def _bundle(
    *,
    bundle_id: str = "bundle-a",
    material_hashes: Counter[str] | None = None,
    latest_marker: datetime | None = None,
    cycle_day_value: date | None = None,
    mixed_cycle: bool = False,
    scope_tokens: frozenset[str] | None = None,
) -> BundlePackage:
    hashes = material_hashes or Counter({"shared": 1})
    return BundlePackage(
        group_key=("source_raw", "binance", "2021-05"),
        bundle_id=bundle_id,
        row_indexes=(0,),
        material_indexes=(0,),
        material_hashes=hashes,
        material_count=sum(hashes.values()),
        logical_hashes={"borrow.csv": Counter(hashes)},
        logical_indexes={"borrow.csv": (0,)},
        latest_marker=latest_marker,
        cycle_day=cycle_day_value,
        mixed_cycle=mixed_cycle,
        scope_tokens=scope_tokens or frozenset(),
    )


def test_extract_datetimes_skips_invalid_tokens_and_deduplicates_compact_minute_values() -> None:
    values = extract_datetimes("bad 202402301200 also 202403091200 and 20240309120059 and 2024_03_09")

    assert datetime(2024, 3, 9, 12, 0, tzinfo=UTC) not in values
    assert datetime(2024, 3, 9, 12, 0, 59, tzinfo=UTC) in values
    assert datetime(2024, 3, 9, 0, 0, tzinfo=UTC) in values


def test_row_marker_and_logical_key_normalize_archive_paths() -> None:
    item = PlannedPackageItem(
        path="/incoming/archive.zip",
        relative_path="folder/202403091530/report.csv",
        archive_source_path="/incoming/archive-202403091545.zip",
        source_folder="binance",
        capture_id="2021-05",
        category="source_raw",
        action="copy",
        sha256="hash",
        bundle_id="bundle-202403091600",
        bundle_relative_path="contents/report.csv",
    )

    assert logical_key("contents/report.csv") == "report.csv"
    assert row_marker(item) == datetime(2024, 3, 9, 16, 0, tzinfo=UTC)


def test_package_sort_key_and_cycle_status_cover_mixed_and_unknown_paths() -> None:
    mixed = _bundle(bundle_id="mixed", mixed_cycle=True)
    unknown = _bundle(bundle_id="unknown")
    dated = _bundle(
        bundle_id="dated",
        latest_marker=datetime(2024, 3, 9, 15, 30, tzinfo=UTC),
        cycle_day_value=date(2024, 3, 9),
    )

    assert package_cycle_status(mixed) == "mixed_cycle"
    assert package_cycle_status(unknown) == "cycle_unknown"
    assert package_cycle_status(dated) == "single_cycle"
    assert package_sort_key(dated) == (20240309153000, "2024-03-09", 1, "dated")


def test_scope_helpers_distinguish_material_scope_partial_scope_and_overlap_reason() -> None:
    left = _bundle(scope_tokens=frozenset({"evm:0x1", "label:main"}))
    right = _bundle(bundle_id="bundle-b", scope_tokens=frozenset({"evm:0x2", "label:main"}))
    partial = _bundle(bundle_id="bundle-c", scope_tokens=frozenset())

    assert material_scope_tokens(left.scope_tokens) == frozenset({"evm:0x1"})
    assert compatible_scope(left, right) is False
    assert scope_status(left, right) == "incompatible_scope"
    assert scope_status(left, partial) == "partial_scope"
    assert overlap_reason("incompatible_scope") == "shared material but explicit scope identifiers differ"


def test_default_and_overlap_review_decisions_cover_mixed_scope_unknown_and_related_merge() -> None:
    primary = _bundle(
        bundle_id="bundle-a",
        latest_marker=datetime(2024, 3, 9, 15, 30, tzinfo=UTC),
        cycle_day_value=date(2024, 3, 9),
    )
    related = _bundle(
        bundle_id="bundle-b",
        latest_marker=datetime(2024, 3, 9, 16, 30, tzinfo=UTC),
        cycle_day_value=date(2024, 3, 9),
    )
    mixed = _bundle(bundle_id="bundle-mixed", mixed_cycle=True, scope_tokens=frozenset({"label:main"}))
    decisions: dict[tuple[str, str, str, str], dict[str, str]] = {}

    mixed_count = apply_default_decisions([primary, related, mixed], decisions)

    assert mixed_count == 1
    assert decisions[package_key(mixed)]["package_status"] == "mixed_cycle_review"
    assert decisions[package_key(primary)]["package_status"] == "primary"

    apply_overlap_review_decisions([primary, related], decisions)
    apply_overlap_review_decisions([primary, related], decisions)

    assert decisions[package_key(primary)]["package_status"] == "overlap_partial_review"
    assert decisions[package_key(primary)]["package_related_bundles"] == "bundle-b"
