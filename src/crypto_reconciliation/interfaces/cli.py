"""CLI entrypoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.application.dtos import (
    BaselineValidateRequest,
    IntakeApplyRequest,
    IntakePlanRequest,
    ManifestRequest,
    NormalizeRequest,
    PdfBalanceExtractRequest,
    ProfileRequest,
    RenderCoinTrackingRequest,
    RoundScaffoldRequest,
    ScreenBatchRequest,
    SourceReconcileRequest,
    StageBatchRequest,
    VerificationCompareRequest,
    WalletInventoryRequest,
    WorkspaceInitRequest,
)
from crypto_reconciliation.application.services import (
    BaselineValidationService,
    BatchScreeningService,
    BatchStagingService,
    CoinTrackingRenderService,
    ManifestService,
    NormalizationService,
    PdfBalanceExtractionService,
    ProfileService,
    RoundScaffoldingService,
    SourceIntakeService,
    SourceReconciliationService,
    VerificationCompareService,
    WalletInventoryService,
    WorkspaceInitializationService,
)
from crypto_reconciliation.application.services.normalize import NormalizationDependencies
from crypto_reconciliation.infrastructure.config import load_app_config
from crypto_reconciliation.infrastructure.discovery import AdapterRegistry, build_registry
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore
from crypto_reconciliation.infrastructure.storage import FilesystemStorage
from crypto_reconciliation.infrastructure.workspace import FilesystemWorkspaceRepository

app = typer.Typer(help="Crypto reconciliation CLI.")
workspace_app = typer.Typer(help="Workspace operations.")
baseline_app = typer.Typer(help="Baseline operations.")
source_app = typer.Typer(help="Source operations.")
source_intake_app = typer.Typer(help="Source intake commands.")
wallet_app = typer.Typer(help="Wallet inventory operations.")
wallet_inventory_app = typer.Typer(help="Wallet inventory commands.")
output_app = typer.Typer(help="Output operations.")
output_render_app = typer.Typer(help="Output rendering commands.")
verification_app = typer.Typer(help="Verification operations.")
batch_app = typer.Typer(help="Import batch operations.")
round_app = typer.Typer(help="Round operations.")
supporting_app = typer.Typer(help="Supporting artifact operations.")

app.add_typer(workspace_app, name="workspace")
app.add_typer(baseline_app, name="baseline")
app.add_typer(source_app, name="source")
app.add_typer(wallet_app, name="wallet")
app.add_typer(output_app, name="output")
app.add_typer(verification_app, name="verification")
app.add_typer(batch_app, name="batch")
app.add_typer(round_app, name="round")
app.add_typer(supporting_app, name="supporting")
wallet_app.add_typer(wallet_inventory_app, name="inventory")
output_app.add_typer(output_render_app, name="render")
source_app.add_typer(source_intake_app, name="intake")


def _runtime_dependencies() -> tuple[AdapterRegistry, FilesystemArtifactStore, FilesystemStorage]:
    return build_registry(), FilesystemArtifactStore(), FilesystemStorage()


def _profile_service() -> ProfileService:
    registry, artifacts, _ = _runtime_dependencies()
    return ProfileService(registry, artifacts)


def _normalization_service() -> NormalizationService:
    registry, artifacts, storage = _runtime_dependencies()
    return NormalizationService(
        NormalizationDependencies(
            source_registry=registry,
            output_registry=registry,
            profile_service=ProfileService(registry, artifacts),
            storage=storage,
            artifacts=artifacts,
        )
    )


def _render_service() -> CoinTrackingRenderService:
    registry, artifacts, _ = _runtime_dependencies()
    return CoinTrackingRenderService(registry, artifacts)


def _emit_response(payload: object) -> None:
    typer.echo(json.dumps(payload, default=str))


@workspace_app.command("init")
def workspace_init(
    workspace_root: Annotated[
        Path | None,
        typer.Option(dir_okay=True, file_okay=False),
    ] = None,
) -> None:
    config = load_app_config()
    resolved_root = workspace_root or config.workspace_root
    response = WorkspaceInitializationService(FilesystemWorkspaceRepository()).execute(
        WorkspaceInitRequest(workspace_root=resolved_root)
    )
    _emit_response(
        {
            "workspace_root": str(response.workspace_root),
            "created_paths": len(response.created_paths),
        }
    )


@baseline_app.command("validate")
def baseline_validate(
    export_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = BaselineValidationService(FilesystemArtifactStore()).execute(
        BaselineValidateRequest(export_dir=export_dir, output_dir=output_dir)
    )
    _emit_response(response.__dict__)


@source_app.command("manifest")
def source_manifest(
    source_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    inspect_archives: Annotated[bool, typer.Option("--inspect-archives/--no-inspect-archives")] = True,
) -> None:
    response = ManifestService(FilesystemArtifactStore()).execute(
        ManifestRequest(source_dir=source_dir, output_path=output, inspect_archives=inspect_archives)
    )
    _emit_response(response.__dict__)


@source_app.command("profile")
def source_profile(
    source: Annotated[str, typer.Option()],
    raw_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    inspect_archives: Annotated[bool, typer.Option("--inspect-archives/--no-inspect-archives")] = True,
) -> None:
    response = _profile_service().execute(
        ProfileRequest(source=source, raw_dir=raw_dir, output_dir=output_dir, inspect_archives=inspect_archives),
    )
    _emit_response(response.__dict__)


@source_app.command("normalize")
def source_normalize(
    source: Annotated[str, typer.Option()],
    raw_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    inspect_archives: Annotated[bool, typer.Option("--inspect-archives/--no-inspect-archives")] = True,
) -> None:
    response = _normalization_service().execute(
        NormalizeRequest(
            source=source,
            raw_dir=raw_dir,
            output_dir=output_dir,
            inspect_archives=inspect_archives,
        )
    )
    _emit_response(response.__dict__)


@source_intake_app.command("plan")
def source_intake_plan(
    incoming_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    workspace_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    report_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    inspect_archives: Annotated[bool, typer.Option("--inspect-archives/--no-inspect-archives")] = True,
) -> None:
    response = SourceIntakeService(FilesystemArtifactStore()).plan(
        IntakePlanRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
            inspect_archives=inspect_archives,
        )
    )
    _emit_response(response.__dict__)


@source_intake_app.command("apply")
def source_intake_apply(
    incoming_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    workspace_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    report_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    inspect_archives: Annotated[bool, typer.Option("--inspect-archives/--no-inspect-archives")] = True,
) -> None:
    response = SourceIntakeService(FilesystemArtifactStore()).apply(
        IntakeApplyRequest(
            incoming_dir=incoming_dir,
            workspace_root=workspace_root,
            report_dir=report_dir,
            inspect_archives=inspect_archives,
        )
    )
    _emit_response(response.__dict__)


@source_app.command("reconcile")
def source_reconcile(
    candidate: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    reference: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = SourceReconciliationService(FilesystemArtifactStore()).execute(
        SourceReconcileRequest(candidate_path=candidate, reference_path=reference, output_dir=output_dir)
    )
    _emit_response(response.__dict__)


@wallet_inventory_app.command("rebuild")
def wallet_inventory_rebuild(
    normalized_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    response = WalletInventoryService(FilesystemArtifactStore()).execute(
        WalletInventoryRequest(normalized_root=normalized_root, output_path=output)
    )
    _emit_response(response.__dict__)


@output_render_app.command("cointracking")
def render_cointracking(
    canonical_events: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    response = _render_service().execute(
        RenderCoinTrackingRequest(canonical_events_path=canonical_events, output_path=output)
    )
    _emit_response(response.__dict__)


@verification_app.command("compare")
def verification_compare(
    previous_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    current_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = VerificationCompareService(FilesystemArtifactStore()).execute(
        VerificationCompareRequest(
            previous_dir=previous_dir,
            current_dir=current_dir,
            output_dir=output_dir,
        )
    )
    _emit_response(response.__dict__)


@batch_app.command("screen")
def batch_screen(
    candidate: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    baseline_export_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = BatchScreeningService(FilesystemArtifactStore()).execute(
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
    response = BatchStagingService(BatchScreeningService(FilesystemArtifactStore())).execute(
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
    workspace_root: Annotated[
        Path | None,
        typer.Option(dir_okay=True, file_okay=False),
    ] = None,
) -> None:
    config = load_app_config()
    response = RoundScaffoldingService(FilesystemArtifactStore()).execute(
        RoundScaffoldRequest(
            workspace_root=workspace_root or config.workspace_root,
            round_id=round_id,
            phase=phase,
            source=source,
        )
    )
    _emit_response(response.__dict__)


@supporting_app.command("extract-pdf-balances")
def extract_pdf_balances(
    pdf: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    statement_kind: Annotated[str | None, typer.Option()] = None,
) -> None:
    response = PdfBalanceExtractionService(FilesystemArtifactStore()).execute(
        PdfBalanceExtractRequest(pdf_path=pdf, output_path=output, statement_kind=statement_kind)
    )
    _emit_response(response.__dict__)


if __name__ == "__main__":
    app()
