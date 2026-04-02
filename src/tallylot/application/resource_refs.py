"""Resource-ref helpers for application boundaries."""

from __future__ import annotations

from pathlib import Path

from tallylot.domain.types import ResourceRef, WorkspacePath


def path_from_ref(ref: ResourceRef | WorkspacePath) -> Path:
    return Path(str(ref))


def to_resource_ref(value: str | Path) -> ResourceRef:
    return ResourceRef(str(value))


def to_workspace_path(value: str | Path) -> WorkspacePath:
    return WorkspacePath(str(value))


def workspace_paths_from_paths(paths: tuple[Path, ...]) -> tuple[WorkspacePath, ...]:
    return tuple(to_workspace_path(path) for path in paths)
