"""Workspace ports."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class WorkspaceLocator(Protocol):
    def resolve(self, override: Path | None = None) -> Path:
        ...


class WorkspaceRepository(Protocol):
    def initialize(self, root: Path) -> tuple[Path, ...]:
        ...
