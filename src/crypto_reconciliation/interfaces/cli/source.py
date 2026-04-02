"""Source CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.application.intake.contracts import (
    IntakeApplyRequest,
    IntakePlanRequest,
    ManifestRequest,
)
from crypto_reconciliation.application.normalization.contracts import NormalizeRequest
from crypto_reconciliation.application.profiling.contracts import ProfileRequest
from crypto_reconciliation.infrastructure.composition.runtime import (
    apply_intake_use_case,
    build_manifest_use_case,
    build_profile_use_case,
    normalize_source_use_case,
    plan_intake_use_case,
)

from .apps import source_app, source_intake_app
from .shared import emit_response


@source_app.command("manifest")
def source_manifest(
    source_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    inspect_archives: Annotated[bool, typer.Option("--inspect-archives/--no-inspect-archives")] = True,
) -> None:
    response = build_manifest_use_case().execute(
        ManifestRequest(source_dir=source_dir, output_path=output, inspect_archives=inspect_archives)
    )
    emit_response(response.__dict__)


@source_app.command("profile")
def source_profile(
    source: Annotated[str, typer.Option()],
    raw_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    inspect_archives: Annotated[bool, typer.Option("--inspect-archives/--no-inspect-archives")] = True,
) -> None:
    response = build_profile_use_case().execute(
        ProfileRequest(source=source, raw_dir=raw_dir, output_dir=output_dir, inspect_archives=inspect_archives),
    )
    emit_response(response.__dict__)


@source_app.command("normalize")
def source_normalize(
    *,  # pylint: disable=too-many-arguments,too-many-positional-arguments
    source: Annotated[str, typer.Option()],
    raw_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    window_start: Annotated[str | None, typer.Option()] = None,
    window_end: Annotated[str | None, typer.Option()] = None,
    inspect_archives: Annotated[bool, typer.Option("--inspect-archives/--no-inspect-archives")] = True,
) -> None:
    response = normalize_source_use_case().execute(
        NormalizeRequest(
            source=source,
            raw_dir=raw_dir,
            output_dir=output_dir,
            window_start=window_start,
            window_end=window_end,
            inspect_archives=inspect_archives,
        )
    )
    emit_response(response.__dict__)


@source_intake_app.command("plan")
def source_intake_plan(
    incoming_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    workspace_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    report_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    inspect_archives: Annotated[bool, typer.Option("--inspect-archives/--no-inspect-archives")] = True,
) -> None:
    response = plan_intake_use_case().execute(
        IntakePlanRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
            inspect_archives=inspect_archives,
        )
    )
    emit_response(response.__dict__)


@source_intake_app.command("apply")
def source_intake_apply(
    incoming_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    workspace_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    report_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    inspect_archives: Annotated[bool, typer.Option("--inspect-archives/--no-inspect-archives")] = True,
) -> None:
    response = apply_intake_use_case().execute(
        IntakeApplyRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
            inspect_archives=inspect_archives,
        )
    )
    emit_response(response.__dict__)
