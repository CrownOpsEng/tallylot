from __future__ import annotations

from crypto_reconciliation.application.intake.packages import apply_package_rules
from tests.support.intake_packages import PackageContext, package_item


def test_apply_package_rules_accumulates_related_overlap_bundles_across_three_packages() -> None:
    items = [
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="202203291730-export/borrow.csv",
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="interest.csv",
            sha256="a-only",
            relative_path="202203291730-export/interest.csv",
        ),
        package_item(
            bundle_id="202203301730-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="202203301730-export/borrow.csv",
        ),
        package_item(
            bundle_id="202203301730-export",
            bundle_relative_path="repay.csv",
            sha256="b-only",
            relative_path="202203301730-export/repay.csv",
        ),
        package_item(
            bundle_id="202203311730-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="202203311730-export/borrow.csv",
        ),
        package_item(
            bundle_id="202203311730-export",
            bundle_relative_path="trades.csv",
            sha256="c-only",
            relative_path="202203311730-export/trades.csv",
        ),
    ]

    resolved, _ = apply_package_rules(items)
    related = {
        item.bundle_id: item.package_related_bundles for item in resolved if item.bundle_relative_path == "borrow.csv"
    }

    assert related["202203291730-export"] == "202203301730-export; 202203311730-export"
    assert related["202203301730-export"] == "202203291730-export; 202203311730-export"
    assert related["202203311730-export"] == "202203291730-export; 202203301730-export"


def test_apply_package_rules_prefers_content_scope_over_conflicting_path_labels() -> None:
    items = [
        package_item(
            bundle_id="202203291830-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="account-main/202203291830-export/borrow.csv",
            context=PackageContext(
                scope_tokens=("evm:0x1111111111111111111111111111111111111111", "label:account-main")
            ),
        ),
        package_item(
            bundle_id="202203291830-export",
            bundle_relative_path="repay.csv",
            sha256="repay",
            relative_path="account-main/202203291830-export/repay.csv",
            context=PackageContext(
                scope_tokens=("evm:0x1111111111111111111111111111111111111111", "label:account-main")
            ),
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="account-alt/202203291730-export/borrow.csv",
            context=PackageContext(
                scope_tokens=("evm:0x1111111111111111111111111111111111111111", "label:account-alt")
            ),
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="interest.csv",
            sha256="interest",
            relative_path="account-alt/202203291730-export/interest.csv",
            context=PackageContext(
                scope_tokens=("evm:0x1111111111111111111111111111111111111111", "label:account-alt")
            ),
        ),
    ]

    resolved, summary = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved if item.bundle_relative_path == "borrow.csv"}

    assert summary.merge_primary_packages == 1
    assert by_bundle["202203291830-export"].package_status == "merge_primary"
    assert by_bundle["202203291730-export"].package_status == "merge_member"
