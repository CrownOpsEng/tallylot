from __future__ import annotations

from crypto_reconciliation.application.intake.packages import apply_package_rules
from tests.support.intake_packages import package_item


def test_apply_package_rules_merges_same_cycle_near_duplicates_and_supersedes_older_conflicts() -> None:
    items = [
        package_item(
            bundle_id="202203291830-export",
            bundle_relative_path="borrow.csv",
            sha256="hash-common",
            relative_path="202203291830-export/borrow.csv",
        ),
        package_item(
            bundle_id="202203291830-export",
            bundle_relative_path="trades.csv",
            sha256="hash-new",
            relative_path="202203291830-export/trades.csv",
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="borrow.csv",
            sha256="hash-common",
            relative_path="202203291730-export/borrow.csv",
        ),
        package_item(
            bundle_id="202203291730-export",
            bundle_relative_path="trades.csv",
            sha256="hash-old",
            relative_path="202203291730-export/trades.csv",
        ),
        package_item(
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


def test_apply_package_rules_merges_unknown_cycle_packages_only_when_additive() -> None:
    items = [
        package_item(
            bundle_id="primary",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="no-date/primary/borrow.csv",
        ),
        package_item(
            bundle_id="primary",
            bundle_relative_path="repay.csv",
            sha256="repay",
            relative_path="no-date/primary/repay.csv",
        ),
        package_item(
            bundle_id="candidate",
            bundle_relative_path="borrow.csv",
            sha256="shared",
            relative_path="no-date/candidate/borrow.csv",
        ),
        package_item(
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
