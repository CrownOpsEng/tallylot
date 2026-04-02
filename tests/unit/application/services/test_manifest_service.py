from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from crypto_reconciliation.application.dtos import ManifestRequest
from crypto_reconciliation.application.services.manifest import ManifestService, _sha256sum_from_text
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_sha256sum_from_text_matches_hashlib_stability() -> None:
    assert _sha256sum_from_text("alpha") == "8ed3f6ad685b959ead7022518e1af76cd816f8e8ec7ccdda1ed4018e8f2223f8"


def test_manifest_service_excludes_output_and_issue_artifacts_from_scan(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    output_path = source_dir / "manifest.csv"

    response = ManifestService(FilesystemArtifactStore()).execute(
        ManifestRequest(source_dir=source_dir, output_path=output_path)
    )

    rows = FilesystemArtifactStore().read_rows(output_path)

    assert response.file_count == 1
    assert rows == [
        {
            "filename": "transactions.csv",
            "archive_source_path": "",
            "archive_member_path": "",
            "size_bytes": str((source_dir / "transactions.csv").stat().st_size),
            "sha256": rows[0]["sha256"],
        }
    ]


def test_manifest_service_writes_archive_member_rows(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    archive_path = source_dir / "bundle.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("inner.csv", "a,b\n1,2\n")

    output_path = tmp_path / "manifest.csv"
    ManifestService(FilesystemArtifactStore()).execute(ManifestRequest(source_dir=source_dir, output_path=output_path))

    rows = FilesystemArtifactStore().read_rows(output_path)

    assert any(row["filename"] == "bundle.zip" for row in rows)
    assert any(row["archive_member_path"] == "inner.csv" for row in rows)
