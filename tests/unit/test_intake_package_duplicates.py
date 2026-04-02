from __future__ import annotations

from crypto_reconciliation.application.services.intake_packages import apply_package_rules
from tests.support.intake_packages import archive_item, package_item


def test_apply_package_rules_marks_identical_older_package_as_duplicate() -> None:
    items = [
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="hash-a",
            relative_path="202203291730-export/borrow.csv",
        ),
        package_item(
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
        archive_item(
            bundle_id="202203291830-export",
            bundle_relative_path="archive/202203291830.zip",
            sha256="archive-hash",
            archive_source_path="202203291830.zip",
        ),
        archive_item(
            bundle_id="202203291830-export",
            bundle_relative_path="contents/trades.csv",
            sha256="shared",
            archive_source_path="202203291830.zip",
        ),
        package_item(
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


def test_apply_package_rules_breaks_identical_unknown_cycle_ties_by_bundle_id() -> None:
    items = [
        package_item(
            bundle_id="bundle-a",
            bundle_relative_path="borrow.csv",
            sha256="hash-a",
            relative_path="no-date/a/borrow.csv",
        ),
        package_item(
            bundle_id="bundle-b",
            bundle_relative_path="borrow.csv",
            sha256="hash-a",
            relative_path="no-date/b/borrow.csv",
        ),
    ]

    resolved, _ = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved}

    assert by_bundle["bundle-a"].package_status == "duplicate_package_identical"
    assert by_bundle["bundle-a"].package_primary_bundle_id == "bundle-b"
    assert by_bundle["bundle-b"].package_status == "primary"


def test_apply_package_rules_compares_archive_only_packages_when_no_contents_exist() -> None:
    items = [
        archive_item(
            bundle_id="202203291730-export",
            bundle_relative_path="archive/older.zip",
            sha256="archive-hash",
            archive_source_path="202203291730.zip",
        ),
        archive_item(
            bundle_id="202203291830-export",
            bundle_relative_path="archive/newer.zip",
            sha256="archive-hash",
            archive_source_path="202203291830.zip",
        ),
    ]

    resolved, summary = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved}

    assert summary.duplicate_packages == 1
    assert by_bundle["202203291730-export"].package_status == "duplicate_package_identical"
    assert by_bundle["202203291830-export"].package_status == "primary"
