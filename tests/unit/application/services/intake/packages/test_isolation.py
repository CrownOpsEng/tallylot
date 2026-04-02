from __future__ import annotations

from crypto_reconciliation.application.services.intake.packages import apply_package_rules
from tests.support.intake_packages import PackageContext, package_item


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
