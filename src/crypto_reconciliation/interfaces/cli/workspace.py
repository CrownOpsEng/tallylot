"""Workspace CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.application.dtos import WorkspaceInitRequest
from crypto_reconciliation.application.services import WorkspaceInitializationService
from crypto_reconciliation.infrastructure.workspace import FilesystemWorkspaceRepository

from .apps import workspace_app
from .runtime import configured_workspace_root
from .shared import emit_response


@workspace_app.command("init")
def workspace_init(
    workspace_root: Annotated[
        Path | None,
        typer.Option(dir_okay=True, file_okay=False),
    ] = None,
) -> None:
    resolved_root = workspace_root or configured_workspace_root()
    response = WorkspaceInitializationService(FilesystemWorkspaceRepository()).execute(
        WorkspaceInitRequest(workspace_root=resolved_root)
    )
    emit_response(
        {
            "workspace_root": str(response.workspace_root),
            "created_paths": len(response.created_paths),
        }
    )
