"""Output CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from tallylot.application.outputs.contracts import RenderOutputRequest
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.composition.runtime import render_output_use_case

from .apps import output_render_app
from .shared import emit_response


@output_render_app.command("file")
def render_output_file(
    output_adapter: Annotated[str, typer.Option()],
    facts: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    response = render_output_use_case().execute(
        RenderOutputRequest(
            output_adapter=output_adapter,
            facts_ref=to_resource_ref(facts),
            output_ref=to_resource_ref(output),
        )
    )
    emit_response(response.__dict__)
