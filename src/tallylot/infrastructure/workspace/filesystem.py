"""Filesystem-backed workspace repository."""

from __future__ import annotations

from pathlib import Path

from tallylot.infrastructure.workspace.layout import SEED_FILES, WORKSPACE_DIRECTORIES


class FilesystemWorkspaceRepository:
    def initialize(self, root: Path) -> tuple[Path, ...]:
        created: list[Path] = []
        for relative_dir in WORKSPACE_DIRECTORIES:
            path = root / relative_dir
            path.mkdir(parents=True, exist_ok=True)
            created.append(path)

        for seed in SEED_FILES:
            target = root / seed.relative_path
            if not target.exists():
                target.write_text(seed.content, encoding="utf-8")
            created.append(target)
        return tuple(created)
