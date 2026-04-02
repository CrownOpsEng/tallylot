"""Wallet inventory CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.application.models.wallet import WalletInventoryRequest
from crypto_reconciliation.application.services import WalletInventoryService
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore

from .apps import wallet_inventory_app
from .shared import emit_response


@wallet_inventory_app.command("rebuild")
def wallet_inventory_rebuild(
    normalized_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    response = WalletInventoryService(FilesystemArtifactStore()).execute(
        WalletInventoryRequest(normalized_root=normalized_root, output_path=output)
    )
    emit_response(response.__dict__)
