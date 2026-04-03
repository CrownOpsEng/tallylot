"""Workspace CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from tallylot.application.workspace.contracts import WorkspaceInitRequest
from tallylot.infrastructure.composition.runtime import (
    configured_workspace_root,
    initialize_workspace_use_case,
)

from .apps import workspace_app
from .shared import emit_response


@workspace_app.command("init")
def workspace_init(
    workspace_root: Annotated[
        Path | None,
        typer.Option(dir_okay=True, file_okay=False),
    ] = None,
) -> None:
    resolved_root = workspace_root or configured_workspace_root()
    response = initialize_workspace_use_case().execute(WorkspaceInitRequest(workspace_root=resolved_root))
    emit_response(
        {
            "workspace_root": str(response.workspace_root),
            "created_paths": len(response.created_paths),
        }
    )
