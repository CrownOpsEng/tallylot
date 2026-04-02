"""Workspace workflow request and response models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceInitRequest:
    workspace_root: Path


@dataclass(frozen=True)
class WorkspaceInitResponse:
    workspace_root: Path
    created_paths: tuple[Path, ...]
