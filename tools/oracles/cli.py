"""Dev-only oracle CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.infrastructure.composition.runtime import configured_workspace_root
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore

from .baseline import BaselineValidationService
from .contracts import (
    BaselineValidateRequest,
    RoundScaffoldRequest,
    ScreenBatchRequest,
    SourceDiffRequest,
    StageBatchRequest,
    VerificationCompareRequest,
)
from .rounds import RoundScaffoldingService
from .source_diff import SourceDiffService
from .staging import BatchScreeningService, BatchStagingService
from .verification import VerificationCompareService

app = typer.Typer(help="Dev-only oracle tooling.")
baseline_app = typer.Typer(help="Baseline oracle commands.")
batch_app = typer.Typer(help="Candidate screening and staging commands.")
round_app = typer.Typer(help="Verification round commands.")
source_app = typer.Typer(help="Source comparison commands.")
verification_app = typer.Typer(help="Verification comparison commands.")

app.add_typer(baseline_app, name="baseline")
app.add_typer(batch_app, name="batch")
app.add_typer(round_app, name="round")
app.add_typer(source_app, name="source")
app.add_typer(verification_app, name="verification")


def _emit_response(payload: object) -> None:
    typer.echo(json.dumps(payload, default=str))


def baseline_validation_service() -> BaselineValidationService:
    return BaselineValidationService(FilesystemArtifactStore())


def batch_screening_service() -> BatchScreeningService:
    return BatchScreeningService(FilesystemArtifactStore())


def batch_staging_service() -> BatchStagingService:
    return BatchStagingService(batch_screening_service())


def round_scaffolding_service() -> RoundScaffoldingService:
    return RoundScaffoldingService(FilesystemArtifactStore())


def source_diff_service() -> SourceDiffService:
    return SourceDiffService(FilesystemArtifactStore())


def verification_compare_service() -> VerificationCompareService:
    return VerificationCompareService(FilesystemArtifactStore())


@baseline_app.command("validate")
def baseline_validate(
    export_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = baseline_validation_service().execute(
        BaselineValidateRequest(export_dir=export_dir, output_dir=output_dir),
    )
    _emit_response(response.__dict__)


@batch_app.command("screen")
def batch_screen(
    candidate: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    baseline_export_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = batch_screening_service().execute(
        ScreenBatchRequest(
            candidate_path=candidate,
            baseline_export_dir=baseline_export_dir,
            output_dir=output_dir,
        )
    )
    _emit_response(response.__dict__)
    if not response.passed:
        raise typer.Exit(code=1)


@batch_app.command("stage")
def batch_stage(
    candidate: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    baseline_export_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    *,  # pylint: disable=too-many-arguments,too-many-positional-arguments
    staged_name: Annotated[str | None, typer.Option()] = None,
    import_ready_dir: Annotated[Path | None, typer.Option(dir_okay=True, file_okay=False)] = None,
    normalization_summary_path: Annotated[
        Path | None,
        typer.Option(dir_okay=False, file_okay=True),
    ] = None,
    window_start: Annotated[str | None, typer.Option()] = None,
    window_end: Annotated[str | None, typer.Option()] = None,
) -> None:
    response = batch_staging_service().execute(
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
    _emit_response(response.__dict__)
    if not response.staged:
        raise typer.Exit(code=1)


@round_app.command("scaffold")
def round_scaffold(
    round_id: Annotated[str, typer.Option()],
    phase: Annotated[str, typer.Option()],
    source: Annotated[str, typer.Option()],
    workspace_root: Annotated[Path | None, typer.Option(dir_okay=True, file_okay=False)] = None,
) -> None:
    response = round_scaffolding_service().execute(
        RoundScaffoldRequest(
            workspace_root=workspace_root or configured_workspace_root(),
            round_id=round_id,
            phase=phase,
            source=source,
        )
    )
    _emit_response(response.__dict__)


@source_app.command("diff")
def source_diff(
    candidate: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    reference: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = source_diff_service().execute(
        SourceDiffRequest(candidate_path=candidate, reference_path=reference, output_dir=output_dir),
    )
    _emit_response(response.__dict__)


@verification_app.command("compare")
def verification_compare(
    previous_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    current_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = verification_compare_service().execute(
        VerificationCompareRequest(previous_dir=previous_dir, current_dir=current_dir, output_dir=output_dir),
    )
    _emit_response(response.__dict__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
