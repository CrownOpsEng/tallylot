"""Checkpoint CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.application.checkpoints.contracts import (
    PdfBalanceExtractRequest,
    WalletInventoryRequest,
)
from crypto_reconciliation.infrastructure.composition.runtime import (
    extract_pdf_balances_use_case,
    rebuild_wallet_inventory_use_case,
)

from .apps import checkpoint_app
from .shared import emit_response


@checkpoint_app.command("rebuild-wallet-inventory")
def rebuild_wallet_inventory(
    normalized_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    response = rebuild_wallet_inventory_use_case().execute(
        WalletInventoryRequest(normalized_root=normalized_root, output_path=output)
    )
    emit_response(response.__dict__)


@checkpoint_app.command("extract-pdf-balances")
def extract_pdf_balances(
    pdf: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    statement_kind: Annotated[str | None, typer.Option()] = None,
) -> None:
    response = extract_pdf_balances_use_case().execute(
        PdfBalanceExtractRequest(pdf_path=pdf, output_path=output, statement_kind=statement_kind)
    )
    emit_response(response.__dict__)
