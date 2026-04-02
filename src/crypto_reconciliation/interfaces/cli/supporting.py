"""Supporting-artifact CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.application.models.source import PdfBalanceExtractRequest
from crypto_reconciliation.application.services import PdfBalanceExtractionService
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore

from .apps import supporting_app
from .shared import emit_response


@supporting_app.command("extract-pdf-balances")
def extract_pdf_balances(
    pdf: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    statement_kind: Annotated[str | None, typer.Option()] = None,
) -> None:
    response = PdfBalanceExtractionService(build_registry(), FilesystemArtifactStore()).execute(
        PdfBalanceExtractRequest(pdf_path=pdf, output_path=output, statement_kind=statement_kind)
    )
    emit_response(response.__dict__)
