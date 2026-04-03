"""Checkpoint CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from tallylot.application.checkpoints.contracts import (
    LocationInventoryRequest,
    PdfBalanceExtractRequest,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.composition.runtime import (
    extract_pdf_balances_use_case,
    rebuild_location_inventory_use_case,
)

from .apps import checkpoint_app
from .shared import emit_response


@checkpoint_app.command("rebuild-location-inventory")
def rebuild_location_inventory(
    normalized_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    response = rebuild_location_inventory_use_case().execute(
        LocationInventoryRequest(
            normalized_dataset_ref=to_resource_ref(normalized_root),
            inventory_output_ref=to_resource_ref(output),
        )
    )
    emit_response(response.__dict__)


@checkpoint_app.command("extract-pdf-balances")
def extract_pdf_balances(
    pdf: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    statement_kind: Annotated[str | None, typer.Option()] = None,
) -> None:
    response = extract_pdf_balances_use_case().execute(
        PdfBalanceExtractRequest(
            pdf_artifact_ref=to_resource_ref(pdf),
            output_ref=to_resource_ref(output),
            statement_kind=statement_kind,
        )
    )
    emit_response(response.__dict__)
