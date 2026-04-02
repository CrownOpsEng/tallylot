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
