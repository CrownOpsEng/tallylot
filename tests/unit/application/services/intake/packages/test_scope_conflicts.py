from __future__ import annotations

from crypto_reconciliation.application.services.intake.packages import apply_package_rules
from tests.support.intake_packages import PackageContext, package_item


def test_apply_package_rules_blocks_merge_when_scope_conflicts() -> None:
    items = [
        package_item(
            bundle_id="202203291830-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="account-main/202203291830-export/borrow.csv",
            context=PackageContext(scope_tokens=("evm:0x1111111111111111111111111111111111111111",)),
        ),
        package_item(
            bundle_id="202203291830-export",
            bundle_relative_path="repay.csv",
            sha256="repay",
            relative_path="account-main/202203291830-export/repay.csv",
            context=PackageContext(scope_tokens=("evm:0x1111111111111111111111111111111111111111",)),
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="account-main/202203291730-export/borrow.csv",
            context=PackageContext(scope_tokens=("evm:0x2222222222222222222222222222222222222222",)),
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="interest.csv",
            sha256="interest",
            relative_path="account-main/202203291730-export/interest.csv",
            context=PackageContext(scope_tokens=("evm:0x2222222222222222222222222222222222222222",)),
        ),
    ]

    resolved, _ = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved if item.bundle_relative_path == "borrow.csv"}

    assert by_bundle["202203291830-export"].package_status == "overlap_partial_review"
    assert by_bundle["202203291830-export"].package_scope_status == "incompatible_scope"
    assert by_bundle["202203291730-export"].package_status == "overlap_partial_review"


def test_apply_package_rules_does_not_merge_packages_for_different_wallet_addresses() -> None:
    items = [
        package_item(
            bundle_id="202203291830-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="0x1111111111111111111111111111111111111111/202203291830-export/borrow.csv",
            context=PackageContext(scope_tokens=("evm:0x1111111111111111111111111111111111111111",)),
        ),
        package_item(
            bundle_id="202203291830-export",
            bundle_relative_path="repay.csv",
            sha256="repay",
            relative_path="0x1111111111111111111111111111111111111111/202203291830-export/repay.csv",
            context=PackageContext(scope_tokens=("evm:0x1111111111111111111111111111111111111111",)),
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="0x2222222222222222222222222222222222222222/202203291730-export/borrow.csv",
            context=PackageContext(scope_tokens=("evm:0x2222222222222222222222222222222222222222",)),
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="interest.csv",
            sha256="interest",
            relative_path="0x2222222222222222222222222222222222222222/202203291730-export/interest.csv",
            context=PackageContext(scope_tokens=("evm:0x2222222222222222222222222222222222222222",)),
        ),
    ]

    resolved, _ = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved if item.bundle_relative_path == "borrow.csv"}

    assert by_bundle["202203291830-export"].package_status == "overlap_partial_review"
    assert by_bundle["202203291730-export"].package_status == "overlap_partial_review"


def test_apply_package_rules_does_not_merge_packages_for_different_account_labels() -> None:
    items = [
        package_item(
            bundle_id="202203291830-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="account-main/202203291830-export/borrow.csv",
            context=PackageContext(scope_tokens=("label:account-main",)),
        ),
        package_item(
            bundle_id="202203291830-export",
            bundle_relative_path="repay.csv",
            sha256="repay",
            relative_path="account-main/202203291830-export/repay.csv",
            context=PackageContext(scope_tokens=("label:account-main",)),
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="account-alt/202203291730-export/borrow.csv",
            context=PackageContext(scope_tokens=("label:account-alt",)),
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="interest.csv",
            sha256="interest",
            relative_path="account-alt/202203291730-export/interest.csv",
            context=PackageContext(scope_tokens=("label:account-alt",)),
        ),
    ]

    resolved, _ = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved if item.bundle_relative_path == "borrow.csv"}

    assert by_bundle["202203291830-export"].package_scope_status == "incompatible_scope"
    assert by_bundle["202203291730-export"].package_status == "overlap_partial_review"


def test_apply_package_rules_blocks_merge_when_content_scope_conflicts_even_if_labels_match() -> None:
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
            relative_path="account-main/202203291730-export/borrow.csv",
            context=PackageContext(
                scope_tokens=("evm:0x2222222222222222222222222222222222222222", "label:account-main")
            ),
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="interest.csv",
            sha256="interest",
            relative_path="account-main/202203291730-export/interest.csv",
            context=PackageContext(
                scope_tokens=("evm:0x2222222222222222222222222222222222222222", "label:account-main")
            ),
        ),
    ]

    resolved, _ = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved if item.bundle_relative_path == "borrow.csv"}

    assert by_bundle["202203291830-export"].package_status == "overlap_partial_review"
    assert by_bundle["202203291830-export"].package_scope_status == "incompatible_scope"
    assert by_bundle["202203291730-export"].package_status == "overlap_partial_review"
