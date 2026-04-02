from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from crypto_reconciliation.application.services.intake import archive_scan
from crypto_reconciliation.application.services.intake.archive_scan import scanned_tree_files


def test_scanned_tree_files_surfaces_oversized_archive_members(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    archive_path = source_dir / "bundle.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("large.csv", "a,b\n1,2\n")

    monkeypatch.setattr(archive_scan, "MAX_ARCHIVE_MEMBER_SIZE_BYTES", 1)

    with scanned_tree_files(source_dir) as scanned_tree:
        issue_kinds = {issue.kind for issue in scanned_tree.issues}
        relative_paths = {item.relative_path for item in scanned_tree.files}

    assert "archive_member_too_large" in issue_kinds
    assert "bundle.zip::large.csv" not in relative_paths


def test_scanned_tree_files_flags_top_level_archives_that_exceed_size_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    archive_path = source_dir / "bundle.zip"
    archive_path.write_bytes(b"PK\x03\x04")

    monkeypatch.setattr(archive_scan, "MAX_ARCHIVE_FILE_SIZE_BYTES", 1)

    with scanned_tree_files(source_dir) as scanned_tree:
        issue_kinds = {issue.kind for issue in scanned_tree.issues}

    assert "archive_too_large" in issue_kinds


def test_scanned_tree_files_flags_nested_archives_that_exceed_size_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    archive_path = source_dir / "bundle.zip"

    nested_bytes = BytesIO()
    with ZipFile(nested_bytes, "w", compression=ZIP_DEFLATED) as nested_archive:
        nested_archive.writestr("nested.csv", "a,b\n3,4\n")

    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("nested.zip", nested_bytes.getvalue())

    monkeypatch.setattr(archive_scan, "MAX_ARCHIVE_FILE_SIZE_BYTES", 1)

    with scanned_tree_files(source_dir) as scanned_tree:
        issue_kinds = {issue.kind for issue in scanned_tree.issues}

    assert "archive_too_large" in issue_kinds


def test_scanned_tree_files_flags_archive_depth_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    archive_path = source_dir / "bundle.zip"

    level_two = BytesIO()
    with ZipFile(level_two, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("inner.csv", "a,b\n1,2\n")

    level_one = BytesIO()
    with ZipFile(level_one, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("nested.zip", level_two.getvalue())

    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("level-one.zip", level_one.getvalue())

    monkeypatch.setattr(archive_scan, "MAX_ARCHIVE_DEPTH", 1)

    with scanned_tree_files(source_dir) as scanned_tree:
        issue_kinds = {issue.kind for issue in scanned_tree.issues}

    assert "archive_depth_limit_exceeded" in issue_kinds


def test_scanned_tree_files_flags_archive_member_count_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    archive_path = source_dir / "bundle.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("one.csv", "a,b\n1,2\n")
        archive.writestr("two.csv", "a,b\n3,4\n")

    monkeypatch.setattr(archive_scan, "MAX_ARCHIVE_MEMBER_COUNT", 1)

    with scanned_tree_files(source_dir) as scanned_tree:
        issue_kinds = {issue.kind for issue in scanned_tree.issues}

    assert "archive_member_limit_exceeded" in issue_kinds


def test_scanned_tree_files_flags_archive_expanded_size_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    archive_path = source_dir / "bundle.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("one.csv", "a,b\n1,2\n")
        archive.writestr("two.csv", "a,b\n3,4\n")

    monkeypatch.setattr(archive_scan, "MAX_ARCHIVE_TOTAL_EXPANDED_BYTES", 5)

    with scanned_tree_files(source_dir) as scanned_tree:
        issue_kinds = {issue.kind for issue in scanned_tree.issues}

    assert "archive_expanded_size_limit_exceeded" in issue_kinds
