"""Reconciliation CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from tallylot.application.balances import (
    BalanceCheckRequest,
    BalanceInspectRequest,
    BalanceSummaryRequest,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.composition.runtime import (
    balance_check_workflow,
    balance_inspect_workflow,
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
        response = balance_inspect_workflow().execute(
            BalanceInspectRequest(
                input_root_ref=to_resource_ref(input_root),
                inspect_output_ref=to_resource_ref(output),
            )
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    emit_response(response.__dict__)


@reconciliation_balances_app.command("check")
def _check_balances(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    input_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    source: Annotated[list[str] | None, typer.Option()] = None,
    as_of: Annotated[list[str] | None, typer.Option("--as-of")] = None,
    timezone: Annotated[
        str,
        typer.Option(
            "--timezone",
            help=(
                "Interpret date-only or naive as-of values in this timezone before "
                "matching exact UTC cutoffs."
            ),
        ),
    ] = "",
    hydrate_missing_references: Annotated[
        bool,
        typer.Option(
            "--hydrate-missing-references/--no-hydrate-missing-references",
            help="Hydrate missing references from balance providers. Default: offline.",
        ),
    ] = False,
    reference_policy: Annotated[str, typer.Option()] = "default",
) -> None:
    try:
        response = balance_check_workflow().execute(
            BalanceCheckRequest(
                input_root_ref=to_resource_ref(input_root),
                output_root_ref=to_resource_ref(output_root),
                sources=tuple(source or ()),
                as_of_values=tuple(as_of or ()),
                timezone=timezone,
                hydrate_missing_references=hydrate_missing_references,
                reference_policy=reference_policy,
            )
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    emit_response(response.__dict__)


@reconciliation_balances_app.command("summarize")
def _summarize_balances(
    inspect: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    check_summary: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    try:
        response = balance_summary_workflow().execute(
            BalanceSummaryRequest(
                inspect_input_ref=to_resource_ref(inspect),
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
