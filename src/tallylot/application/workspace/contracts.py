"""Workspace capability request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.types import WorkspacePath


@dataclass(frozen=True)
class WorkspaceInitRequest:
    workspace_root_ref: WorkspacePath


@dataclass(frozen=True)
class WorkspaceInitResponse:
    workspace_root_ref: WorkspacePath
    created_refs: tuple[WorkspacePath, ...]
