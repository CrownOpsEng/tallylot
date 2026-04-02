"""Verification CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.application.models.verification import VerificationCompareRequest
from crypto_reconciliation.application.services import VerificationCompareService
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore

from .apps import verification_app
from .shared import emit_response


@verification_app.command("compare")
def verification_compare(
    previous_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    current_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = VerificationCompareService(FilesystemArtifactStore()).execute(
        VerificationCompareRequest(
            previous_dir=previous_dir,
            current_dir=current_dir,
            output_dir=output_dir,
        )
    )
    emit_response(response.__dict__)
