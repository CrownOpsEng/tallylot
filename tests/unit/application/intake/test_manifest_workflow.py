from __future__ import annotations

from pathlib import Path

from tallylot.application.intake import ManifestRequest
from tallylot.application.intake.build_manifest import BuildManifestUseCase
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_manifest_service_writes_manifest(structured_source_dir: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "manifest.csv"

    response = BuildManifestUseCase(FilesystemArtifactStore()).execute(
        ManifestRequest(source_dir=structured_source_dir, output_path=output_path),
    )

    assert response.file_count == 1
    assert response.manifest_fingerprint
    assert output_path.exists()


def test_manifest_service_excludes_manifest_output_from_source_scan(
    structured_source_dir: Path,
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    (source_dir / "transactions.csv").write_text(
        (structured_source_dir / "transactions.csv").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    output_path = source_dir / "manifest.csv"
    service = BuildManifestUseCase(FilesystemArtifactStore())

    first = service.execute(ManifestRequest(source_dir=source_dir, output_path=output_path))
    second = service.execute(ManifestRequest(source_dir=source_dir, output_path=output_path))

    assert first.file_count == 1
    assert second.file_count == 1
    assert first.manifest_fingerprint == second.manifest_fingerprint
