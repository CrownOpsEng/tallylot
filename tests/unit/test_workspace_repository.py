from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.infrastructure.workspace import FilesystemWorkspaceRepository


def test_workspace_repository_initializes_seed_files(tmp_path: Path) -> None:
    repository = FilesystemWorkspaceRepository()

    created_paths = repository.initialize(tmp_path)

    assert created_paths
    assert (tmp_path / "analysis/issues/issue_log.csv").exists()
    assert (tmp_path / "outputs/logs/round_log.csv").exists()
    assert (tmp_path / "config/workspace.json").exists()
