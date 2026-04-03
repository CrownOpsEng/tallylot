from __future__ import annotations

from crypto_reconciliation.application.services.intake_packages import (
    PlannedPackageItem,
    apply_package_rules,
)


def _item(
    *,
    bundle_id: str,
    bundle_relative_path: str,
    sha256: str,
    relative_path: str,
    scope_tokens: tuple[str, ...] = (),
) -> PlannedPackageItem:
    return PlannedPackageItem(
        path=f"/incoming/{relative_path}",
        relative_path=relative_path,
        archive_source_path="",
        source_folder="binance",
        capture_id="2021-05",
        category="source_raw",
        action="copy",
        sha256=sha256,
        bundle_id=bundle_id,
        bundle_relative_path=bundle_relative_path,
        scope_tokens=scope_tokens,
    )


def _archive_item(
    *,
    bundle_id: str,
    bundle_relative_path: str,
    sha256: str,
    archive_source_path: str,
) -> PlannedPackageItem:
    return PlannedPackageItem(
        path=f"/incoming/{archive_source_path}",
        relative_path=archive_source_path,
        archive_source_path=f"/incoming/{archive_source_path}",
        source_folder="binance",
        capture_id="2021-05",
        category="source_raw",
        action="extract_copy" if bundle_relative_path.startswith("contents/") else "copy",
        sha256=sha256,
        bundle_id=bundle_id,
        bundle_relative_path=bundle_relative_path,
    )


def test_apply_package_rules_merges_same_cycle_near_duplicates_and_supersedes_older_conflicts() -> None:
    items = [
        _item(
            bundle_id="202203291830-export",
            bundle_relative_path="borrow.csv",
            sha256="hash-common",
            relative_path="202203291830-export/borrow.csv",
        ),
        _item(
            bundle_id="202203291830-export",
            bundle_relative_path="trades.csv",
            sha256="hash-new",
            relative_path="202203291830-export/trades.csv",
        ),
        _item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="hash-common",
            relative_path="202203291730-export/borrow.csv",
        ),
        _item(
            bundle_id="202203291730-export",
            bundle_relative_path="trades.csv",
            sha256="hash-old",
            relative_path="202203291730-export/trades.csv",
        ),
        _item(
            bundle_id="202203291730-export",
            bundle_relative_path="interest.csv",
            sha256="hash-interest",
            relative_path="202203291730-export/interest.csv",
        ),
    ]

    resolved, summary = apply_package_rules(items)
    by_path = {item.relative_path: item for item in resolved}

    assert summary.merge_primary_packages == 1
    assert by_path["202203291830-export/borrow.csv"].package_status == "merge_primary"
    assert by_path["202203291730-export/borrow.csv"].package_status == "merge_member"
    assert by_path["202203291730-export/borrow.csv"].package_row_status == "package_merge_into_primary"
    assert by_path["202203291730-export/trades.csv"].package_row_status == "package_merge_superseded_skip"
    assert by_path["202203291730-export/trades.csv"].action == "skip"


def test_apply_package_rules_keeps_different_cycle_exports_separate() -> None:
    items = [
        _item(
            bundle_id="202203301830-export",
            bundle_relative_path="borrow.csv",
            sha256="hash-common",
            relative_path="202203301830-export/borrow.csv",
        ),
        _item(
            bundle_id="202203301830-export",
            bundle_relative_path="repay.csv",
            sha256="hash-repay",
            relative_path="202203301830-export/repay.csv",
        ),
        _item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="hash-common",
            relative_path="202203291730-export/borrow.csv",
        ),
        _item(
            bundle_id="202203291730-export",
            bundle_relative_path="interest.csv",
            sha256="hash-interest",
            relative_path="202203291730-export/interest.csv",
        ),
    ]

    resolved, summary = apply_package_rules(items)
    statuses = {item.bundle_id: item.package_status for item in resolved if item.bundle_relative_path == "borrow.csv"}

    assert summary.overlap_packages == 2
    assert statuses["202203301830-export"] == "overlap_partial_review"
    assert statuses["202203291730-export"] == "overlap_partial_review"


def test_apply_package_rules_flags_mixed_cycle_bundles() -> None:
    items = [
        _item(
            bundle_id="mixed-cycle",
            bundle_relative_path="borrow.csv",
            sha256="hash-a",
            relative_path="folder/202203291730/borrow.csv",
        ),
        _item(
            bundle_id="mixed-cycle",
            bundle_relative_path="repay.csv",
            sha256="hash-b",
            relative_path="folder/202203301730/repay.csv",
        ),
    ]

    resolved, summary = apply_package_rules(items)

    assert summary.mixed_cycle_packages == 1
    assert resolved[0].package_status == "mixed_cycle_review"
    assert resolved[1].package_cycle_status == "mixed_cycle"


def test_apply_package_rules_marks_identical_older_package_as_duplicate() -> None:
    items = [
        _item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="hash-a",
            relative_path="202203291730-export/borrow.csv",
        ),
        _item(
            bundle_id="202203291830-export",
            bundle_relative_path="borrow.csv",
            sha256="hash-a",
            relative_path="202203291830-export/borrow.csv",
        ),
    ]

    resolved, summary = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved}

    assert summary.duplicate_packages == 1
    assert by_bundle["202203291730-export"].package_status == "duplicate_package_identical"
    assert by_bundle["202203291730-export"].action == "skip"
    assert by_bundle["202203291830-export"].package_status == "primary"


def test_apply_package_rules_ignores_archive_wrapper_when_matching_contents() -> None:
    items = [
        _archive_item(
            bundle_id="202203291830-export",
            bundle_relative_path="archive/202203291830.zip",
            sha256="archive-hash",
            archive_source_path="202203291830.zip",
        ),
        _archive_item(
            bundle_id="202203291830-export",
            bundle_relative_path="contents/trades.csv",
            sha256="shared",
            archive_source_path="202203291830.zip",
        ),
        _item(
            bundle_id="202203291730-export",
            bundle_relative_path="trades.csv",
            sha256="shared",
            relative_path="202203291730-export/trades.csv",
        ),
    ]

    resolved, summary = apply_package_rules(items)
    older = next(item for item in resolved if item.bundle_id == "202203291730-export")

    assert summary.duplicate_packages == 1
    assert older.package_status == "duplicate_package_identical"


def test_apply_package_rules_merges_unknown_cycle_packages_only_when_additive() -> None:
    items = [
        _item(
            bundle_id="primary",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="no-date/primary/borrow.csv",
        ),
        _item(
            bundle_id="primary",
            bundle_relative_path="repay.csv",
            sha256="repay",
            relative_path="no-date/primary/repay.csv",
        ),
        _item(
            bundle_id="candidate",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="no-date/candidate/borrow.csv",
        ),
        _item(
            bundle_id="candidate",
            bundle_relative_path="interest.csv",
            sha256="interest",
            relative_path="no-date/candidate/interest.csv",
        ),
    ]

    resolved, summary = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved if item.bundle_relative_path == "borrow.csv"}

    assert summary.merge_primary_packages == 1
    assert by_bundle["primary"].package_status == "merge_primary"
    assert by_bundle["candidate"].package_status == "merge_member"


def test_apply_package_rules_blocks_merge_when_scope_conflicts() -> None:
    items = [
        _item(
            bundle_id="202203291830-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="account-main/202203291830-export/borrow.csv",
            scope_tokens=("evm:0x1111111111111111111111111111111111111111",),
        ),
        _item(
            bundle_id="202203291830-export",
            bundle_relative_path="repay.csv",
            sha256="repay",
            relative_path="account-main/202203291830-export/repay.csv",
            scope_tokens=("evm:0x1111111111111111111111111111111111111111",),
        ),
        _item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="account-main/202203291730-export/borrow.csv",
            scope_tokens=("evm:0x2222222222222222222222222222222222222222",),
        ),
        _item(
            bundle_id="202203291730-export",
            bundle_relative_path="interest.csv",
            sha256="interest",
            relative_path="account-main/202203291730-export/interest.csv",
            scope_tokens=("evm:0x2222222222222222222222222222222222222222",),
        ),
    ]

    resolved, _ = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved if item.bundle_relative_path == "borrow.csv"}

    assert by_bundle["202203291830-export"].package_status == "overlap_partial_review"
    assert by_bundle["202203291830-export"].package_scope_status == "incompatible_scope"
    assert by_bundle["202203291730-export"].package_status == "overlap_partial_review"
