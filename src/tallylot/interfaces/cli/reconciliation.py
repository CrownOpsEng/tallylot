"""Reconciliation CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from tallylot.application.reconciliation.contracts import BalanceAssertionRequest
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.composition.runtime import assert_balances_use_case

from .apps import reconciliation_app
from .shared import emit_response


@reconciliation_app.command("assert-balances")
def _assert_balances(
    snapshots: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    evidence: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    response = assert_balances_use_case().execute(
        BalanceAssertionRequest(
            snapshot_input_ref=to_resource_ref(snapshots),
            evidence_input_ref=to_resource_ref(evidence),
            assertion_output_ref=to_resource_ref(output),
        )
    )
    emit_response(response.__dict__)


_COMMAND_CALLBACKS = (_assert_balances,)
