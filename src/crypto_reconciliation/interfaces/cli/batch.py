"""Import-batch CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.application.dtos import ScreenBatchRequest, StageBatchRequest
from crypto_reconciliation.application.services import BatchScreeningService, BatchStagingService
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore

from .apps import batch_app
from .shared import emit_response


@batch_app.command("screen")
def batch_screen(
    candidate: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    baseline_export_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = BatchScreeningService(build_registry(), FilesystemArtifactStore()).execute(
        ScreenBatchRequest(
            candidate_path=candidate,
            baseline_export_dir=baseline_export_dir,
            output_dir=output_dir,
        )
    )
    emit_response(response.__dict__)
    if not response.passed:
        raise typer.Exit(code=1)


@batch_app.command("stage")
def batch_stage(
    candidate: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    baseline_export_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    *,  # pylint: disable=too-many-arguments
    staged_name: Annotated[str | None, typer.Option()] = None,
    import_ready_dir: Annotated[
        Path | None,
        typer.Option(dir_okay=True, file_okay=False),
    ] = None,
    normalization_summary_path: Annotated[
        Path | None,
        typer.Option(dir_okay=False, file_okay=True),
    ] = None,
    window_start: Annotated[str | None, typer.Option()] = None,
    window_end: Annotated[str | None, typer.Option()] = None,
) -> None:
    response = BatchStagingService(BatchScreeningService(build_registry(), FilesystemArtifactStore())).execute(
        StageBatchRequest(
            candidate_path=candidate,
            baseline_export_dir=baseline_export_dir,
            output_dir=output_dir,
            staged_name=staged_name,
            import_ready_dir=import_ready_dir,
            normalization_summary_path=normalization_summary_path,
            window_start=window_start,
            window_end=window_end,
        )
    )
    emit_response(response.__dict__)
    if not response.staged:
        raise typer.Exit(code=1)
