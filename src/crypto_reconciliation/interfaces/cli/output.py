"""Output CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.application.dtos import RenderOutputRequest

from .apps import output_render_app
from .runtime import render_service
from .shared import emit_response


@output_render_app.command("file")
def render_output_file(
    output_adapter: Annotated[str, typer.Option()],
    canonical_events: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    response = render_service().execute(
        RenderOutputRequest(
            output_adapter=output_adapter,
            canonical_events_path=canonical_events,
            output_path=output,
        )
    )
    emit_response(response.__dict__)
