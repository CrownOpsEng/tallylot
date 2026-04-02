"""CLI entrypoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from crypto_reconciliation.application.dtos import (
    BaselineValidateRequest,
    ManifestRequest,
    NormalizeRequest,
    ProfileRequest,
    RenderCoinTrackingRequest,
    StageBatchRequest,
    VerificationCompareRequest,
    WalletInventoryRequest,
    WorkspaceInitRequest,
)
from crypto_reconciliation.application.services import (
    BaselineValidationService,
    BatchStagingService,
    CoinTrackingRenderService,
    ManifestService,
    NormalizationService,
    ProfileService,
    VerificationCompareService,
    WalletInventoryService,
    WorkspaceInitializationService,
)
from crypto_reconciliation.infrastructure.config import load_app_config
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.storage import FilesystemStorage
from crypto_reconciliation.infrastructure.workspace import FilesystemWorkspaceRepository

app = typer.Typer(help="Crypto reconciliation CLI.")
workspace_app = typer.Typer(help="Workspace operations.")
baseline_app = typer.Typer(help="Baseline operations.")
source_app = typer.Typer(help="Source operations.")
wallet_app = typer.Typer(help="Wallet inventory operations.")
wallet_inventory_app = typer.Typer(help="Wallet inventory commands.")
output_app = typer.Typer(help="Output operations.")
output_render_app = typer.Typer(help="Output rendering commands.")
verification_app = typer.Typer(help="Verification operations.")
batch_app = typer.Typer(help="Import batch operations.")

app.add_typer(workspace_app, name="workspace")
app.add_typer(baseline_app, name="baseline")
app.add_typer(source_app, name="source")
app.add_typer(wallet_app, name="wallet")
app.add_typer(output_app, name="output")
app.add_typer(verification_app, name="verification")
app.add_typer(batch_app, name="batch")
wallet_app.add_typer(wallet_inventory_app, name="inventory")
output_app.add_typer(output_render_app, name="render")


def _services() -> tuple[
    ProfileService,
    NormalizationService,
    CoinTrackingRenderService,
]:
    registry = build_registry()
    profile_service = ProfileService(registry)
    storage = FilesystemStorage()
    normalization_service = NormalizationService(registry, profile_service, storage)
    render_service = CoinTrackingRenderService(registry)
    return profile_service, normalization_service, render_service


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
    typer.echo(
        json.dumps(
            {
                "workspace_root": str(response.workspace_root),
                "created_paths": len(response.created_paths),
            },
        ),
    )


@baseline_app.command("validate")
def baseline_validate(
    export_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = BaselineValidationService().execute(
        BaselineValidateRequest(export_dir=export_dir, output_dir=output_dir)
    )
    typer.echo(json.dumps(response.__dict__, default=str))


@source_app.command("manifest")
def source_manifest(
    source_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    response = ManifestService().execute(ManifestRequest(source_dir=source_dir, output_path=output))
    typer.echo(json.dumps(response.__dict__, default=str))


@source_app.command("profile")
def source_profile(
    source: Annotated[str, typer.Option()],
    raw_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    profile_service, _, _ = _services()
    response = profile_service.execute(
        ProfileRequest(source=source, raw_dir=raw_dir, output_dir=output_dir),
    )
    typer.echo(json.dumps(response.__dict__, default=str))


@source_app.command("normalize")
def source_normalize(
    source: Annotated[str, typer.Option()],
    raw_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    _, normalization_service, _ = _services()
    response = normalization_service.execute(
        NormalizeRequest(source=source, raw_dir=raw_dir, output_dir=output_dir)
    )
    typer.echo(json.dumps(response.__dict__, default=str))


@wallet_inventory_app.command("rebuild")
def wallet_inventory_rebuild(
    normalized_root: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    response = WalletInventoryService().execute(
        WalletInventoryRequest(normalized_root=normalized_root, output_path=output)
    )
    typer.echo(json.dumps(response.__dict__, default=str))


@output_render_app.command("cointracking")
def render_cointracking(
    canonical_events: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    output: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
) -> None:
    _, _, render_service = _services()
    response = render_service.execute(
        RenderCoinTrackingRequest(canonical_events_path=canonical_events, output_path=output)
    )
    typer.echo(json.dumps(response.__dict__, default=str))


@verification_app.command("compare")
def verification_compare(
    previous_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    current_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = VerificationCompareService().execute(
        VerificationCompareRequest(
            previous_dir=previous_dir,
            current_dir=current_dir,
            output_dir=output_dir,
        )
    )
    typer.echo(json.dumps(response.__dict__, default=str))


@batch_app.command("stage")
def batch_stage(
    candidate: Annotated[Path, typer.Option(dir_okay=False, file_okay=True)],
    baseline_export_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option(dir_okay=True, file_okay=False)],
) -> None:
    response = BatchStagingService().execute(
        StageBatchRequest(
            candidate_path=candidate,
            baseline_export_dir=baseline_export_dir,
            output_dir=output_dir,
        )
    )
    typer.echo(json.dumps(response.__dict__, default=str))


if __name__ == "__main__":
    app()
