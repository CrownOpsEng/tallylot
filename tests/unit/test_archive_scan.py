from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from crypto_reconciliation.application.dtos import ManifestRequest
from crypto_reconciliation.application.services.archive_scan import scanned_tree_files
from crypto_reconciliation.application.services.manifest import ManifestService
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_scanned_tree_files_inspects_nested_zip_members(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    archive_path = source_dir / "bundle.zip"

    nested_bytes = BytesIO()
    with ZipFile(nested_bytes, "w", compression=ZIP_DEFLATED) as nested_archive:
        nested_archive.writestr("nested.csv", "a,b\n3,4\n")

    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("inner.csv", "a,b\n1,2\n")
        archive.writestr("nested.zip", nested_bytes.getvalue())

    with scanned_tree_files(source_dir) as scanned_tree:
        relative_paths = {item.relative_path for item in scanned_tree.files}

    assert "bundle.zip" in relative_paths
    assert "bundle.zip::inner.csv" in relative_paths
    assert "bundle.zip::nested.zip" in relative_paths
    assert "bundle.zip::nested.zip::nested.csv" in relative_paths


def test_scanned_tree_files_surfaces_unsafe_archive_member_paths(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    archive_path = source_dir / "bundle.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("../evil.csv", "a,b\n1,2\n")

    with scanned_tree_files(source_dir) as scanned_tree:
        issue_kinds = {issue.kind for issue in scanned_tree.issues}

    assert "unsafe_archive_member_path" in issue_kinds


def test_manifest_service_can_opt_out_of_archive_member_inspection(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    archive_path = source_dir / "bundle.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("inner.csv", "a,b\n1,2\n")

    service = ManifestService(FilesystemArtifactStore())
    manifest_path = tmp_path / "manifest.csv"

    response = service.execute(
        ManifestRequest(
            source_dir=source_dir,
            output_path=manifest_path,
            inspect_archives=False,
        )
    )

    rows = FilesystemArtifactStore().read_rows(manifest_path)

    assert response.file_count == 1
    assert rows[0]["filename"] == "bundle.zip"
    assert rows[0]["archive_source_path"] == ""
