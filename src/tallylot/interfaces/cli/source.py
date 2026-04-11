"""Source CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from tallylot.application.intake.contracts import (
    IntakeApplyRequest,
    IntakePlanRequest,
    ManifestRequest,
)
from tallylot.application.capture_paths import (
    default_capture_normalized_root,
    source_assembled_root,
)
from tallylot.application.normalization.contracts import (
    AssembleSourceRequest,
    NormalizeRequest,
)
from tallylot.application.profiling.contracts import ProfileRequest
from tallylot.application.resource_refs import to_resource_ref, to_workspace_path
from tallylot.infrastructure.composition.runtime import (
    assemble_source_use_case,
    apply_intake_use_case,
    build_manifest_use_case,
    build_profile_use_case,
    configured_workspace_root,
    normalize_source_use_case,
    plan_intake_use_case,
)

from .apps import source_app, source_intake_app
from .shared import emit_response


@source_app.command("manifest")
def _source_manifest(
    source_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    inspect_archives: Annotated[
        bool, typer.Option("--inspect-archives/--no-inspect-archives")
    ] = True,
) -> None:
    response = build_manifest_use_case().execute(
        ManifestRequest(
            source_capture_ref=to_resource_ref(source_dir),
            manifest_output_ref=to_resource_ref(output),
            inspect_archives=inspect_archives,
        )
    )
    emit_response(response.__dict__)


@source_app.command("profile")
def _source_profile(
    source: Annotated[str, typer.Option()],
    raw_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[
        Path | None, typer.Option(dir_okay=True, file_okay=False)
    ] = None,
    inspect_archives: Annotated[
        bool, typer.Option("--inspect-archives/--no-inspect-archives")
    ] = True,
) -> None:
    try:
        resolved_output_dir = output_dir or default_capture_normalized_root(raw_dir)
        response = build_profile_use_case().execute(
            ProfileRequest(
                source=source,
                raw_capture_ref=to_resource_ref(raw_dir),
                profile_output_ref=to_resource_ref(resolved_output_dir),
                inspect_archives=inspect_archives,
            ),
        )
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(2) from exc
    emit_response(response.__dict__)


@source_app.command("normalize")
def _source_normalize(
    *,  # pylint: disable=too-many-arguments,too-many-positional-arguments
    source: Annotated[str, typer.Option()],
    raw_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[
        Path | None, typer.Option(dir_okay=True, file_okay=False)
    ] = None,
    window_start: Annotated[str | None, typer.Option()] = None,
    window_end: Annotated[str | None, typer.Option()] = None,
    inspect_archives: Annotated[
        bool, typer.Option("--inspect-archives/--no-inspect-archives")
    ] = True,
) -> None:
    try:
        resolved_output_dir = output_dir or default_capture_normalized_root(raw_dir)
        response = normalize_source_use_case().execute(
            NormalizeRequest(
                source=source,
                raw_capture_ref=to_resource_ref(raw_dir),
                normalized_output_ref=to_resource_ref(resolved_output_dir),
                window_start=window_start,
                window_end=window_end,
                inspect_archives=inspect_archives,
            )
        )
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(2) from exc
    emit_response(response.__dict__)


@source_app.command("assemble")
def _source_assemble(
    source: Annotated[str, typer.Option()],
    workspace_root: Annotated[
        Path | None, typer.Option(dir_okay=True, file_okay=False)
    ] = None,
    output_dir: Annotated[
        Path | None, typer.Option(dir_okay=True, file_okay=False)
    ] = None,
) -> None:
    resolved_workspace_root = workspace_root or configured_workspace_root()
    resolved_output_dir = output_dir or source_assembled_root(
        resolved_workspace_root,
        source,
    )
    response = assemble_source_use_case().execute(
        AssembleSourceRequest(
            source=source,
            workspace_root_ref=to_resource_ref(resolved_workspace_root),
            assembled_output_ref=to_resource_ref(resolved_output_dir),
        )
    )
    emit_response(response.__dict__)


@source_intake_app.command("plan")
def _source_intake_plan(
    incoming_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    workspace_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    report_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    inspect_archives: Annotated[
        bool, typer.Option("--inspect-archives/--no-inspect-archives")
    ] = True,
) -> None:
    response = plan_intake_use_case().execute(
        IntakePlanRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
            inspect_archives=inspect_archives,
        )
    )
    emit_response(response.__dict__)


@source_intake_app.command("apply")
def _source_intake_apply(
    incoming_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    workspace_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    report_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    inspect_archives: Annotated[
        bool, typer.Option("--inspect-archives/--no-inspect-archives")
    ] = True,
) -> None:
    response = apply_intake_use_case().execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(workspace_root),
            report_output_ref=to_resource_ref(report_dir),
            inspect_archives=inspect_archives,
        )
    )
    emit_response(response.__dict__)
    if response.capture_status != "captured":
        raise typer.Exit(1)


_COMMAND_CALLBACKS = (
    _source_manifest,
    _source_profile,
    _source_normalize,
    _source_assemble,
    _source_intake_plan,
    _source_intake_apply,
)
