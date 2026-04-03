"""Source CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.application.dtos import (
    IntakeApplyRequest,
    IntakePlanRequest,
    ManifestRequest,
    NormalizeRequest,
    ProfileRequest,
    SourceReconcileRequest,
)
from crypto_reconciliation.application.services import ManifestService, SourceIntakeService, SourceReconciliationService
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore

from .apps import source_app, source_intake_app
from .runtime import normalization_service, profile_service
from .shared import emit_response


@source_app.command("manifest")
def source_manifest(
    source_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    inspect_archives: Annotated[bool, typer.Option("--inspect-archives/--no-inspect-archives")] = True,
) -> None:
    response = ManifestService(FilesystemArtifactStore()).execute(
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
    response = profile_service().execute(
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
    response = normalization_service().execute(
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
    response = SourceIntakeService(build_registry(), FilesystemArtifactStore()).plan(
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
    response = SourceIntakeService(build_registry(), FilesystemArtifactStore()).apply(
        IntakeApplyRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
            inspect_archives=inspect_archives,
        )
    )
    emit_response(response.__dict__)


@source_app.command("reconcile")
def source_reconcile(
    candidate: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    reference: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = SourceReconciliationService(FilesystemArtifactStore()).execute(
        SourceReconcileRequest(candidate_path=candidate, reference_path=reference, output_dir=output_dir)
    )
    emit_response(response.__dict__)
