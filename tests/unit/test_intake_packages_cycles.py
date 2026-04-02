from __future__ import annotations

from crypto_reconciliation.application.services.intake_packages import apply_package_rules
from tests.support.intake_packages import PackageContext, archive_item, package_item


def test_apply_package_rules_does_not_treat_single_range_filename_as_mixed_cycle() -> None:
    items = [
        package_item(
            bundle_id="range-bundle",
            bundle_relative_path="Binance Transaction History 2021-05-01 to 2021-08-01.csv",
            sha256="hash-a",
            relative_path="Binance Transaction History 2021-05-01 to 2021-08-01.csv",
        )
    ]

    resolved, _ = apply_package_rules(items)

    assert resolved[0].package_status == "primary"
    assert resolved[0].package_cycle_status == "single_cycle"


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


def test_apply_package_rules_isolates_different_capture_ids() -> None:
    items = [
        package_item(
            bundle_id="same-name",
            bundle_relative_path="borrow.csv",
            sha256="hash-a",
            relative_path="202203291730-export/borrow.csv",
            context=PackageContext(capture_id="2021-05"),
        ),
        package_item(
            bundle_id="same-name",
            bundle_relative_path="borrow.csv",
            sha256="hash-a",
            relative_path="202203291830-export/borrow.csv",
            context=PackageContext(capture_id="2021-06"),
        ),
    ]

    resolved, _ = apply_package_rules(items)
    may = next(item for item in resolved if item.capture_id == "2021-05")
    june = next(item for item in resolved if item.capture_id == "2021-06")

    assert may.package_status == "primary"
    assert june.package_status == "primary"


def test_apply_package_rules_isolates_different_sources() -> None:
    items = [
        package_item(
            bundle_id="same-name",
            bundle_relative_path="borrow.csv",
            sha256="hash-a",
            relative_path="binance/202203291730-export/borrow.csv",
            context=PackageContext(source_folder="binance"),
        ),
        package_item(
            bundle_id="same-name",
            bundle_relative_path="borrow.csv",
            sha256="hash-a",
            relative_path="coinbase/202203291830-export/borrow.csv",
            context=PackageContext(source_folder="coinbase"),
        ),
    ]

    resolved, _ = apply_package_rules(items)
    binance = next(item for item in resolved if item.source_folder == "binance")
    coinbase = next(item for item in resolved if item.source_folder == "coinbase")

    assert binance.package_status == "primary"
    assert coinbase.package_status == "primary"


def test_apply_package_rules_keeps_disjoint_same_cycle_packages_separate() -> None:
    items = [
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="hash-a",
            relative_path="202203291730-export/borrow.csv",
        ),
        package_item(
            bundle_id="202203291830-export",
            bundle_relative_path="repay.csv",
            sha256="hash-b",
            relative_path="202203291830-export/repay.csv",
        ),
    ]

    resolved, _ = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved}

    assert by_bundle["202203291730-export"].package_status == "primary"
    assert by_bundle["202203291830-export"].package_status == "primary"


def test_apply_package_rules_keeps_unknown_cycle_conflicts_as_overlap_review() -> None:
    items = [
        package_item(
            bundle_id="primary",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="no-date/primary/borrow.csv",
        ),
        package_item(
            bundle_id="primary",
            bundle_relative_path="trades.csv",
            sha256="old",
            relative_path="no-date/primary/trades.csv",
        ),
        package_item(
            bundle_id="candidate",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="no-date/candidate/borrow.csv",
        ),
        package_item(
            bundle_id="candidate",
            bundle_relative_path="trades.csv",
            sha256="new",
            relative_path="no-date/candidate/trades.csv",
        ),
    ]

    resolved, _ = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved if item.bundle_relative_path == "borrow.csv"}

    assert by_bundle["primary"].package_status == "overlap_partial_review"
    assert by_bundle["candidate"].package_status == "overlap_partial_review"


def test_apply_package_rules_does_not_merge_single_cycle_with_mixed_cycle_bundle() -> None:
    items = [
        package_item(
            bundle_id="mixed",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="folder/202203291730/borrow.csv",
        ),
        package_item(
            bundle_id="mixed",
            bundle_relative_path="interest.csv",
            sha256="interest",
            relative_path="folder/202203301730/interest.csv",
        ),
        package_item(
            bundle_id="single",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="202203291830-export/borrow.csv",
        ),
        package_item(
            bundle_id="single",
            bundle_relative_path="repay.csv",
            sha256="repay",
            relative_path="202203291830-export/repay.csv",
        ),
    ]

    resolved, _ = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved if item.bundle_relative_path == "borrow.csv"}

    assert by_bundle["mixed"].package_status == "mixed_cycle_review"
    assert by_bundle["single"].package_status == "primary"


def test_apply_package_rules_keeps_same_end_day_range_files_in_single_cycle_bundle() -> None:
    items = [
        package_item(
            bundle_id="range-bundle",
            bundle_relative_path="Binance Transaction History 2021-05-01 to 2021-08-01.csv",
            sha256="hash-a",
            relative_path="Binance Transaction History 2021-05-01 to 2021-08-01.csv",
        ),
        package_item(
            bundle_id="range-bundle",
            bundle_relative_path="Borrow History 2021-07-01 to 2021-08-01.csv",
            sha256="hash-b",
            relative_path="Borrow History 2021-07-01 to 2021-08-01.csv",
        ),
    ]

    resolved, _ = apply_package_rules(items)

    assert resolved[0].package_status == "primary"
    assert resolved[0].package_cycle_status == "single_cycle"


def test_apply_package_rules_flags_bundle_when_range_end_days_disagree() -> None:
    items = [
        package_item(
            bundle_id="range-bundle",
            bundle_relative_path="Binance Transaction History 2021-05-01 to 2021-08-01.csv",
            sha256="hash-a",
            relative_path="Binance Transaction History 2021-05-01 to 2021-08-01.csv",
        ),
        package_item(
            bundle_id="range-bundle",
            bundle_relative_path="Borrow History 2021-07-01 to 2021-08-20.csv",
            sha256="hash-b",
            relative_path="Borrow History 2021-07-01 to 2021-08-20.csv",
        ),
    ]

    resolved, summary = apply_package_rules(items)

    assert summary.mixed_cycle_packages == 1
    assert resolved[0].package_status == "mixed_cycle_review"
