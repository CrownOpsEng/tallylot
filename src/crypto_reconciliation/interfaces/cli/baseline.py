"""Baseline CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.application.dtos import BaselineValidateRequest
from crypto_reconciliation.application.services import BaselineValidationService
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore

from .apps import baseline_app
from .shared import emit_response


@baseline_app.command("validate")
def baseline_validate(
    export_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = BaselineValidationService(build_registry(), FilesystemArtifactStore()).execute(
        BaselineValidateRequest(export_dir=export_dir, output_dir=output_dir)
    )
    emit_response(response.__dict__)
