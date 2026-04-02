"""Round CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.application.models.rounds import RoundScaffoldRequest
from crypto_reconciliation.application.services import RoundScaffoldingService
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore

from .apps import round_app
from .runtime import configured_workspace_root
from .shared import emit_response


@round_app.command("scaffold")
def round_scaffold(
    round_id: Annotated[str, typer.Option()],
    phase: Annotated[str, typer.Option()],
    source: Annotated[str, typer.Option()],
    workspace_root: Annotated[
        Path | None,
        typer.Option(dir_okay=True, file_okay=False),
    ] = None,
) -> None:
    response = RoundScaffoldingService(FilesystemArtifactStore()).execute(
        RoundScaffoldRequest(
            workspace_root=workspace_root or configured_workspace_root(),
            round_id=round_id,
            phase=phase,
            source=source,
        )
    )
    emit_response(response.__dict__)
