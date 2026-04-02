from __future__ import annotations

import package_resolution


def make_row(
    *,
    bundle_id: str,
    bundle_relative_path: str,
    sha256: str,
    source_path: str,
    role: str = "source_raw",
    source_folder: str = "binance",
    capture_id: str = "2021-05",
) -> dict[str, str]:
    return {
        "role": role,
        "source_folder": source_folder,
        "capture_id": capture_id,
        "bundle_id": bundle_id,
        "bundle_relative_path": bundle_relative_path,
        "sha256": sha256,
        "source_path": source_path,
        "archive_source_path": "",
        "path": source_path,
    }


def make_archive_row(
    *,
    bundle_id: str,
    member_name: str,
    sha256: str,
    archive_source_path: str,
    role: str = "source_raw",
    source_folder: str = "binance",
    capture_id: str = "2021-05",
) -> dict[str, str]:
    return {
        "role": role,
        "source_folder": source_folder,
        "capture_id": capture_id,
        "bundle_id": bundle_id,
        "bundle_relative_path": f"archive/{member_name}",
        "sha256": sha256,
        "source_path": archive_source_path,
        "archive_source_path": "",
        "path": archive_source_path,
    }


def make_archive_content_row(
    *,
    bundle_id: str,
    member_name: str,
    sha256: str,
    archive_source_path: str,
    role: str = "source_raw",
    source_folder: str = "binance",
    capture_id: str = "2021-05",
) -> dict[str, str]:
    return {
        "role": role,
        "source_folder": source_folder,
        "capture_id": capture_id,
        "bundle_id": bundle_id,
        "bundle_relative_path": f"contents/{member_name}",
        "sha256": sha256,
        "source_path": f"{archive_source_path}::{member_name}",
        "archive_source_path": archive_source_path,
        "path": f"{archive_source_path}::{member_name}",
    }


def test_resolve_bundle_packages_merges_same_cycle_near_duplicates_and_supersedes_older_conflicts() -> None:
    rows = [
        make_row(bundle_id="202203291830-export", bundle_relative_path="borrow.csv", sha256="hash-common", source_path="/incoming/202203291830-export/borrow.csv"),
        make_row(bundle_id="202203291830-export", bundle_relative_path="trades.csv", sha256="hash-new", source_path="/incoming/202203291830-export/trades.csv"),
        make_row(bundle_id="202203291730-export", bundle_relative_path="borrow.csv", sha256="hash-common", source_path="/incoming/202203291730-export/borrow.csv"),
        make_row(bundle_id="202203291730-export", bundle_relative_path="trades.csv", sha256="hash-old", source_path="/incoming/202203291730-export/trades.csv"),
        make_row(bundle_id="202203291730-export", bundle_relative_path="interest.csv", sha256="hash-interest", source_path="/incoming/202203291730-export/interest.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    primary_key = ("source_raw", "binance", "2021-05", "202203291830-export")
    member_key = ("source_raw", "binance", "2021-05", "202203291730-export")
    assert resolution.package_decisions[primary_key]["package_status"] == "merge_primary"
    assert resolution.package_decisions[member_key]["package_status"] == "merge_member"
    assert resolution.row_actions[2]["package_row_status"] == "package_merge_into_primary"
    assert resolution.row_actions[2]["effective_bundle_id"] == "202203291830-export"
    assert resolution.row_actions[3]["package_row_status"] == "package_merge_superseded_skip"
    assert resolution.row_actions[4]["package_row_status"] == "package_merge_into_primary"


def test_resolve_bundle_packages_keeps_different_cycle_exports_separate() -> None:
    rows = [
        make_row(bundle_id="202203301830-export", bundle_relative_path="borrow.csv", sha256="hash-common", source_path="/incoming/202203301830-export/borrow.csv"),
        make_row(bundle_id="202203301830-export", bundle_relative_path="repay.csv", sha256="hash-repay", source_path="/incoming/202203301830-export/repay.csv"),
        make_row(bundle_id="202203291730-export", bundle_relative_path="borrow.csv", sha256="hash-common", source_path="/incoming/202203291730-export/borrow.csv"),
        make_row(bundle_id="202203291730-export", bundle_relative_path="interest.csv", sha256="hash-interest", source_path="/incoming/202203291730-export/interest.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    left_key = ("source_raw", "binance", "2021-05", "202203301830-export")
    right_key = ("source_raw", "binance", "2021-05", "202203291730-export")
    assert resolution.package_decisions[left_key]["package_status"] == "overlap_partial_review"
    assert resolution.package_decisions[right_key]["package_status"] == "overlap_partial_review"
    assert all(action["package_row_status"] == "package_keep" for action in resolution.row_actions.values())


def test_resolve_bundle_packages_flags_mixed_cycle_bundles() -> None:
    rows = [
        make_row(bundle_id="folder-bundle", bundle_relative_path="borrow.csv", sha256="hash-a", source_path="/incoming/folder/202203291730/borrow.csv"),
        make_row(bundle_id="folder-bundle", bundle_relative_path="repay.csv", sha256="hash-b", source_path="/incoming/folder/202203301730/repay.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    bundle_key = ("source_raw", "binance", "2021-05", "folder-bundle")
    assert resolution.package_decisions[bundle_key]["package_status"] == "mixed_cycle_review"
    assert resolution.package_decisions[bundle_key]["package_cycle_status"] == "mixed_cycle"


def test_resolve_bundle_packages_does_not_treat_single_range_filename_as_mixed_cycle() -> None:
    rows = [
        make_row(
            bundle_id="range-bundle",
            bundle_relative_path="Binance Transaction History 2021-05-01 to 2021-08-01.csv",
            sha256="hash-a",
            source_path="/incoming/Binance Transaction History 2021-05-01 to 2021-08-01.csv",
        )
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    bundle_key = ("source_raw", "binance", "2021-05", "range-bundle")
    assert resolution.package_decisions[bundle_key]["package_status"] == "primary"
    assert resolution.package_decisions[bundle_key]["package_cycle_status"] == "single_cycle"


def test_resolve_bundle_packages_marks_identical_older_package_as_duplicate() -> None:
    rows = [
        make_row(bundle_id="202203291730-export", bundle_relative_path="borrow.csv", sha256="hash-a", source_path="/incoming/202203291730-export/borrow.csv"),
        make_row(bundle_id="202203291830-export", bundle_relative_path="borrow.csv", sha256="hash-a", source_path="/incoming/202203291830-export/borrow.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    older_key = ("source_raw", "binance", "2021-05", "202203291730-export")
    newer_key = ("source_raw", "binance", "2021-05", "202203291830-export")
    assert resolution.package_decisions[older_key]["package_status"] == "duplicate_package_identical"
    assert resolution.package_decisions[older_key]["package_primary_bundle_id"] == "202203291830-export"
    assert resolution.package_decisions[newer_key]["package_status"] == "primary"
    assert resolution.row_actions[0]["package_row_status"] == "package_duplicate_skip"
    assert resolution.row_actions[1]["package_row_status"] == "package_keep"


def test_resolve_bundle_packages_breaks_identical_unknown_cycle_ties_by_bundle_id() -> None:
    rows = [
        make_row(bundle_id="bundle-a", bundle_relative_path="borrow.csv", sha256="hash-a", source_path="/incoming/no-date/a/borrow.csv"),
        make_row(bundle_id="bundle-b", bundle_relative_path="borrow.csv", sha256="hash-a", source_path="/incoming/no-date/b/borrow.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    a_key = ("source_raw", "binance", "2021-05", "bundle-a")
    b_key = ("source_raw", "binance", "2021-05", "bundle-b")
    assert resolution.package_decisions[a_key]["package_status"] == "duplicate_package_identical"
    assert resolution.package_decisions[a_key]["package_primary_bundle_id"] == "bundle-b"
    assert resolution.package_decisions[b_key]["package_status"] == "primary"


def test_resolve_bundle_packages_ignores_archive_wrapper_when_matching_extracted_contents() -> None:
    rows = [
        make_archive_row(bundle_id="202203291830-export", member_name="202203291830.zip", sha256="archive-hash", archive_source_path="/incoming/202203291830.zip"),
        make_archive_content_row(bundle_id="202203291830-export", member_name="trades.csv", sha256="shared", archive_source_path="/incoming/202203291830.zip"),
        make_row(bundle_id="202203291730-export", bundle_relative_path="trades.csv", sha256="shared", source_path="/incoming/202203291730-export/trades.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    older_key = ("source_raw", "binance", "2021-05", "202203291730-export")
    newer_key = ("source_raw", "binance", "2021-05", "202203291830-export")
    assert resolution.package_decisions[older_key]["package_status"] == "duplicate_package_identical"
    assert resolution.package_decisions[older_key]["package_primary_bundle_id"] == "202203291830-export"
    assert resolution.package_decisions[newer_key]["package_status"] == "primary"


def test_resolve_bundle_packages_compares_archive_only_packages_when_no_contents_exist() -> None:
    rows = [
        make_archive_row(bundle_id="202203291730-export", member_name="older.zip", sha256="archive-hash", archive_source_path="/incoming/202203291730.zip"),
        make_archive_row(bundle_id="202203291830-export", member_name="newer.zip", sha256="archive-hash", archive_source_path="/incoming/202203291830.zip"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    older_key = ("source_raw", "binance", "2021-05", "202203291730-export")
    newer_key = ("source_raw", "binance", "2021-05", "202203291830-export")
    assert resolution.package_decisions[older_key]["package_status"] == "duplicate_package_identical"
    assert resolution.package_decisions[newer_key]["package_status"] == "primary"


def test_resolve_bundle_packages_isolates_different_capture_ids() -> None:
    rows = [
        make_row(bundle_id="same-name", bundle_relative_path="borrow.csv", sha256="hash-a", source_path="/incoming/202203291730-export/borrow.csv", capture_id="2021-05"),
        make_row(bundle_id="same-name", bundle_relative_path="borrow.csv", sha256="hash-a", source_path="/incoming/202203291830-export/borrow.csv", capture_id="2021-06"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    may_key = ("source_raw", "binance", "2021-05", "same-name")
    jun_key = ("source_raw", "binance", "2021-06", "same-name")
    assert resolution.package_decisions[may_key]["package_status"] == "primary"
    assert resolution.package_decisions[jun_key]["package_status"] == "primary"


def test_resolve_bundle_packages_isolates_different_sources() -> None:
    rows = [
        make_row(bundle_id="same-name", bundle_relative_path="borrow.csv", sha256="hash-a", source_path="/incoming/binance/202203291730-export/borrow.csv", source_folder="binance"),
        make_row(bundle_id="same-name", bundle_relative_path="borrow.csv", sha256="hash-a", source_path="/incoming/coinbase/202203291830-export/borrow.csv", source_folder="coinbase"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    binance_key = ("source_raw", "binance", "2021-05", "same-name")
    coinbase_key = ("source_raw", "coinbase", "2021-05", "same-name")
    assert resolution.package_decisions[binance_key]["package_status"] == "primary"
    assert resolution.package_decisions[coinbase_key]["package_status"] == "primary"


def test_resolve_bundle_packages_keeps_disjoint_same_cycle_packages_separate() -> None:
    rows = [
        make_row(bundle_id="202203291730-export", bundle_relative_path="borrow.csv", sha256="hash-a", source_path="/incoming/202203291730-export/borrow.csv"),
        make_row(bundle_id="202203291830-export", bundle_relative_path="repay.csv", sha256="hash-b", source_path="/incoming/202203291830-export/repay.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    left_key = ("source_raw", "binance", "2021-05", "202203291730-export")
    right_key = ("source_raw", "binance", "2021-05", "202203291830-export")
    assert resolution.package_decisions[left_key]["package_status"] == "primary"
    assert resolution.package_decisions[right_key]["package_status"] == "primary"


def test_resolve_bundle_packages_merges_unknown_cycle_packages_only_when_additive() -> None:
    rows = [
        make_row(bundle_id="primary", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/no-date/primary/borrow.csv"),
        make_row(bundle_id="primary", bundle_relative_path="repay.csv", sha256="repay", source_path="/incoming/no-date/primary/repay.csv"),
        make_row(bundle_id="candidate", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/no-date/candidate/borrow.csv"),
        make_row(bundle_id="candidate", bundle_relative_path="interest.csv", sha256="interest", source_path="/incoming/no-date/candidate/interest.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    primary_key = ("source_raw", "binance", "2021-05", "primary")
    candidate_key = ("source_raw", "binance", "2021-05", "candidate")
    assert resolution.package_decisions[primary_key]["package_status"] == "merge_primary"
    assert resolution.package_decisions[candidate_key]["package_status"] == "merge_member"
    assert resolution.row_actions[2]["package_row_status"] == "package_merge_into_primary"
    assert resolution.row_actions[3]["package_row_status"] == "package_merge_into_primary"


def test_resolve_bundle_packages_keeps_unknown_cycle_conflicts_as_overlap_review() -> None:
    rows = [
        make_row(bundle_id="primary", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/no-date/primary/borrow.csv"),
        make_row(bundle_id="primary", bundle_relative_path="trades.csv", sha256="old", source_path="/incoming/no-date/primary/trades.csv"),
        make_row(bundle_id="candidate", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/no-date/candidate/borrow.csv"),
        make_row(bundle_id="candidate", bundle_relative_path="trades.csv", sha256="new", source_path="/incoming/no-date/candidate/trades.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    primary_key = ("source_raw", "binance", "2021-05", "primary")
    candidate_key = ("source_raw", "binance", "2021-05", "candidate")
    assert resolution.package_decisions[primary_key]["package_status"] == "overlap_partial_review"
    assert resolution.package_decisions[candidate_key]["package_status"] == "overlap_partial_review"
    assert all(action["package_row_status"] == "package_keep" for action in resolution.row_actions.values())


def test_resolve_bundle_packages_does_not_merge_single_cycle_with_mixed_cycle_bundle() -> None:
    rows = [
        make_row(bundle_id="mixed", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/folder/202203291730/borrow.csv"),
        make_row(bundle_id="mixed", bundle_relative_path="interest.csv", sha256="interest", source_path="/incoming/folder/202203301730/interest.csv"),
        make_row(bundle_id="single", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/202203291830-export/borrow.csv"),
        make_row(bundle_id="single", bundle_relative_path="repay.csv", sha256="repay", source_path="/incoming/202203291830-export/repay.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    mixed_key = ("source_raw", "binance", "2021-05", "mixed")
    single_key = ("source_raw", "binance", "2021-05", "single")
    assert resolution.package_decisions[mixed_key]["package_status"] == "mixed_cycle_review"
    assert resolution.package_decisions[single_key]["package_status"] == "primary"


def test_resolve_bundle_packages_accumulates_related_overlap_bundles_across_three_packages() -> None:
    rows = [
        make_row(bundle_id="202203291730-export", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/202203291730-export/borrow.csv"),
        make_row(bundle_id="202203291730-export", bundle_relative_path="interest.csv", sha256="a-only", source_path="/incoming/202203291730-export/interest.csv"),
        make_row(bundle_id="202203301730-export", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/202203301730-export/borrow.csv"),
        make_row(bundle_id="202203301730-export", bundle_relative_path="repay.csv", sha256="b-only", source_path="/incoming/202203301730-export/repay.csv"),
        make_row(bundle_id="202203311730-export", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/202203311730-export/borrow.csv"),
        make_row(bundle_id="202203311730-export", bundle_relative_path="trades.csv", sha256="c-only", source_path="/incoming/202203311730-export/trades.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    first_key = ("source_raw", "binance", "2021-05", "202203291730-export")
    second_key = ("source_raw", "binance", "2021-05", "202203301730-export")
    third_key = ("source_raw", "binance", "2021-05", "202203311730-export")
    assert resolution.package_decisions[first_key]["package_related_bundles"] == "202203301730-export; 202203311730-export"
    assert resolution.package_decisions[second_key]["package_related_bundles"] == "202203291730-export; 202203311730-export"
    assert resolution.package_decisions[third_key]["package_related_bundles"] == "202203291730-export; 202203301730-export"


def test_resolve_bundle_packages_merges_multiple_same_cycle_members_into_one_primary() -> None:
    rows = [
        make_row(bundle_id="202203291930-export", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/202203291930-export/borrow.csv"),
        make_row(bundle_id="202203291930-export", bundle_relative_path="repay.csv", sha256="repay", source_path="/incoming/202203291930-export/repay.csv"),
        make_row(bundle_id="202203291830-export", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/202203291830-export/borrow.csv"),
        make_row(bundle_id="202203291830-export", bundle_relative_path="interest.csv", sha256="interest", source_path="/incoming/202203291830-export/interest.csv"),
        make_row(bundle_id="202203291730-export", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/202203291730-export/borrow.csv"),
        make_row(bundle_id="202203291730-export", bundle_relative_path="trades.csv", sha256="trades", source_path="/incoming/202203291730-export/trades.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    primary_key = ("source_raw", "binance", "2021-05", "202203291930-export")
    middle_key = ("source_raw", "binance", "2021-05", "202203291830-export")
    older_key = ("source_raw", "binance", "2021-05", "202203291730-export")
    assert resolution.package_decisions[primary_key]["package_status"] == "merge_primary"
    assert resolution.package_decisions[primary_key]["package_related_bundles"] == "202203291730-export; 202203291830-export"
    assert resolution.package_decisions[middle_key]["package_status"] == "merge_member"
    assert resolution.package_decisions[older_key]["package_status"] == "merge_member"


def test_resolve_bundle_packages_requires_strictly_newer_marker_to_supersede_conflicts() -> None:
    rows = [
        make_row(bundle_id="202203291830-export-a", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/202203291830-export-a/borrow.csv"),
        make_row(bundle_id="202203291830-export-a", bundle_relative_path="trades.csv", sha256="old", source_path="/incoming/202203291830-export-a/trades.csv"),
        make_row(bundle_id="202203291830-export-b", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/202203291830-export-b/borrow.csv"),
        make_row(bundle_id="202203291830-export-b", bundle_relative_path="trades.csv", sha256="new", source_path="/incoming/202203291830-export-b/trades.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    first_key = ("source_raw", "binance", "2021-05", "202203291830-export-a")
    second_key = ("source_raw", "binance", "2021-05", "202203291830-export-b")
    assert resolution.package_decisions[first_key]["package_status"] == "overlap_partial_review"
    assert resolution.package_decisions[second_key]["package_status"] == "overlap_partial_review"


def test_resolve_bundle_packages_keeps_same_end_day_range_files_in_single_cycle_bundle() -> None:
    rows = [
        make_row(
            bundle_id="range-bundle",
            bundle_relative_path="Binance Transaction History 2021-05-01 to 2021-08-01.csv",
            sha256="hash-a",
            source_path="/incoming/Binance Transaction History 2021-05-01 to 2021-08-01.csv",
        ),
        make_row(
            bundle_id="range-bundle",
            bundle_relative_path="Borrow History 2021-07-01 to 2021-08-01.csv",
            sha256="hash-b",
            source_path="/incoming/Borrow History 2021-07-01 to 2021-08-01.csv",
        ),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    bundle_key = ("source_raw", "binance", "2021-05", "range-bundle")
    assert resolution.package_decisions[bundle_key]["package_status"] == "primary"
    assert resolution.package_decisions[bundle_key]["package_cycle_status"] == "single_cycle"


def test_resolve_bundle_packages_flags_bundle_when_range_end_days_disagree() -> None:
    rows = [
        make_row(
            bundle_id="range-bundle",
            bundle_relative_path="Binance Transaction History 2021-05-01 to 2021-08-01.csv",
            sha256="hash-a",
            source_path="/incoming/Binance Transaction History 2021-05-01 to 2021-08-01.csv",
        ),
        make_row(
            bundle_id="range-bundle",
            bundle_relative_path="Borrow History 2021-07-01 to 2021-08-20.csv",
            sha256="hash-b",
            source_path="/incoming/Borrow History 2021-07-01 to 2021-08-20.csv",
        ),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    bundle_key = ("source_raw", "binance", "2021-05", "range-bundle")
    assert resolution.package_decisions[bundle_key]["package_status"] == "mixed_cycle_review"


def test_resolve_bundle_packages_does_not_merge_packages_for_different_wallet_addresses() -> None:
    rows = [
        make_row(bundle_id="202203291830-export", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/0x1111111111111111111111111111111111111111/202203291830-export/borrow.csv"),
        make_row(bundle_id="202203291830-export", bundle_relative_path="repay.csv", sha256="repay", source_path="/incoming/0x1111111111111111111111111111111111111111/202203291830-export/repay.csv"),
        make_row(bundle_id="202203291730-export", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/0x2222222222222222222222222222222222222222/202203291730-export/borrow.csv"),
        make_row(bundle_id="202203291730-export", bundle_relative_path="interest.csv", sha256="interest", source_path="/incoming/0x2222222222222222222222222222222222222222/202203291730-export/interest.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    newer_key = ("source_raw", "binance", "2021-05", "202203291830-export")
    older_key = ("source_raw", "binance", "2021-05", "202203291730-export")
    assert resolution.package_decisions[newer_key]["package_status"] == "overlap_partial_review"
    assert resolution.package_decisions[older_key]["package_status"] == "overlap_partial_review"


def test_resolve_bundle_packages_does_not_merge_packages_for_different_account_labels() -> None:
    rows = [
        make_row(bundle_id="202203291830-export", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/account-main/202203291830-export/borrow.csv"),
        make_row(bundle_id="202203291830-export", bundle_relative_path="repay.csv", sha256="repay", source_path="/incoming/account-main/202203291830-export/repay.csv"),
        make_row(bundle_id="202203291730-export", bundle_relative_path="borrow.csv", sha256="shared", source_path="/incoming/account-margin/202203291730-export/borrow.csv"),
        make_row(bundle_id="202203291730-export", bundle_relative_path="interest.csv", sha256="interest", source_path="/incoming/account-margin/202203291730-export/interest.csv"),
    ]

    resolution = package_resolution.resolve_bundle_packages(rows)

    newer_key = ("source_raw", "binance", "2021-05", "202203291830-export")
    older_key = ("source_raw", "binance", "2021-05", "202203291730-export")
    assert resolution.package_decisions[newer_key]["package_status"] == "overlap_partial_review"
    assert resolution.package_decisions[older_key]["package_status"] == "overlap_partial_review"
