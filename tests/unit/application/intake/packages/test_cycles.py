from __future__ import annotations

from crypto_reconciliation.application.intake.packages import apply_package_rules
from tests.support.intake_packages import package_item


def test_apply_package_rules_keeps_different_cycle_exports_separate() -> None:
    items = [
        package_item(
            bundle_id="202203301830-export",
            bundle_relative_path="borrow.csv",
            sha256="hash-common",
            relative_path="202203301830-export/borrow.csv",
        ),
        package_item(
            bundle_id="202203301830-export",
            bundle_relative_path="repay.csv",
            sha256="hash-repay",
            relative_path="202203301830-export/repay.csv",
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="hash-common",
            relative_path="202203291730-export/borrow.csv",
        ),
        package_item(
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
        package_item(
            bundle_id="mixed-cycle",
            bundle_relative_path="borrow.csv",
            sha256="hash-a",
            relative_path="folder/202203291730/borrow.csv",
        ),
        package_item(
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
