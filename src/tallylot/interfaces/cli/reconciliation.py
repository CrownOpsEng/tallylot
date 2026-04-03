"""Reconciliation CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from tallylot.application.reconciliation import (
    BalanceCheckRequest,
    BalanceCoverageRequest,
    BalanceSummaryRequest,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.composition.runtime import (
    balance_check_workflow,
    balance_coverage_workflow,
    balance_summary_workflow,
)

from .apps import reconciliation_balances_app
from .shared import emit_response


@reconciliation_balances_app.command("inspect")
def _inspect_balances(
    input_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    try:
        response = balance_coverage_workflow().execute(
            BalanceCoverageRequest(
                input_root_ref=to_resource_ref(input_root),
                coverage_output_ref=to_resource_ref(output),
            )
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    emit_response(response.__dict__)


@reconciliation_balances_app.command("check")
def _check_balances(
    input_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    source: Annotated[list[str] | None, typer.Option()] = None,
) -> None:
    try:
        response = balance_check_workflow().execute(
            BalanceCheckRequest(
                input_root_ref=to_resource_ref(input_root),
                output_root_ref=to_resource_ref(output_root),
                sources=tuple(source or ()),
            )
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    emit_response(response.__dict__)


@reconciliation_balances_app.command("summarize")
def _summarize_balances(
    coverage: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    check_summary: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    try:
        response = balance_summary_workflow().execute(
            BalanceSummaryRequest(
                coverage_input_ref=to_resource_ref(coverage),
                check_summary_input_ref=to_resource_ref(check_summary),
                summary_output_ref=to_resource_ref(output),
            )
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    emit_response(response.__dict__)


_COMMAND_CALLBACKS = (
    _inspect_balances,
    _check_balances,
    _summarize_balances,
)
