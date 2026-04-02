from __future__ import annotations

from crypto_reconciliation.application.services.intake_packages import apply_package_rules
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


def test_apply_package_rules_merges_multiple_same_cycle_members_into_one_primary() -> None:
    items = [
        package_item(
            bundle_id="202203291930-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="202203291930-export/borrow.csv",
        ),
        package_item(
            bundle_id="202203291930-export",
            bundle_relative_path="repay.csv",
            sha256="repay",
            relative_path="202203291930-export/repay.csv",
        ),
        package_item(
            bundle_id="202203291830-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="202203291830-export/borrow.csv",
        ),
        package_item(
            bundle_id="202203291830-export",
            bundle_relative_path="interest.csv",
            sha256="interest",
            relative_path="202203291830-export/interest.csv",
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="202203291730-export/borrow.csv",
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="trades.csv",
            sha256="trades",
            relative_path="202203291730-export/trades.csv",
        ),
    ]

    resolved, summary = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved if item.bundle_relative_path == "borrow.csv"}

    assert summary.merge_primary_packages == 1
    assert summary.merged_packages == 2
    assert by_bundle["202203291930-export"].package_status == "merge_primary"
    assert by_bundle["202203291930-export"].package_related_bundles == "202203291730-export; 202203291830-export"
    assert by_bundle["202203291830-export"].package_status == "merge_member"
    assert by_bundle["202203291730-export"].package_status == "merge_member"


def test_apply_package_rules_requires_strictly_newer_marker_to_supersede_conflicts() -> None:
    items = [
        package_item(
            bundle_id="202203291830-export-a",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="202203291830-export-a/borrow.csv",
        ),
        package_item(
            bundle_id="202203291830-export-a",
            bundle_relative_path="trades.csv",
            sha256="old",
            relative_path="202203291830-export-a/trades.csv",
        ),
        package_item(
            bundle_id="202203291830-export-b",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="202203291830-export-b/borrow.csv",
        ),
        package_item(
            bundle_id="202203291830-export-b",
            bundle_relative_path="trades.csv",
            sha256="new",
            relative_path="202203291830-export-b/trades.csv",
        ),
    ]

    resolved, _ = apply_package_rules(items)
    by_bundle = {item.bundle_id: item for item in resolved if item.bundle_relative_path == "borrow.csv"}

    assert by_bundle["202203291830-export-a"].package_status == "overlap_partial_review"
    assert by_bundle["202203291830-export-b"].package_status == "overlap_partial_review"


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
