"""Composition-root builders for the CLI and library runtime."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.checkpoints.extract_pdf_balances import ExtractPdfBalancesUseCase
from crypto_reconciliation.application.checkpoints.rebuild_wallet_inventory import RebuildWalletInventoryUseCase
from crypto_reconciliation.application.intake.apply_intake import ApplyIntakeUseCase
from crypto_reconciliation.application.intake.build_manifest import BuildManifestUseCase
from crypto_reconciliation.application.intake.plan_intake import PlanIntakeUseCase
from crypto_reconciliation.application.normalization.normalize_source import (
    NormalizationDependencies,
    NormalizeSourceUseCase,
)
from crypto_reconciliation.application.outputs.render_output import RenderOutputUseCase
from crypto_reconciliation.application.profiling.build_profile import BuildProfileUseCase
from crypto_reconciliation.application.workspace.initialize_workspace import InitializeWorkspaceUseCase
from crypto_reconciliation.infrastructure.config import load_app_config
from crypto_reconciliation.infrastructure.discovery import AdapterRegistry, build_registry
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore
from crypto_reconciliation.infrastructure.storage import FilesystemEvidenceRepository, FilesystemFactRepository
from crypto_reconciliation.infrastructure.workspace import FilesystemWorkspaceRepository


def runtime_dependencies() -> tuple[
    AdapterRegistry,
    FilesystemArtifactStore,
    FilesystemFactRepository,
    FilesystemEvidenceRepository,
]:
    return build_registry(), FilesystemArtifactStore(), FilesystemFactRepository(), FilesystemEvidenceRepository()


def build_manifest_use_case() -> BuildManifestUseCase:
    _, artifacts, _, _ = runtime_dependencies()
    return BuildManifestUseCase(artifacts)


def build_profile_use_case() -> BuildProfileUseCase:
    registry, artifacts, _, _ = runtime_dependencies()
    return BuildProfileUseCase(registry, artifacts)


def normalize_source_use_case() -> NormalizeSourceUseCase:
    registry, artifacts, facts, evidence = runtime_dependencies()
    return NormalizeSourceUseCase(
        NormalizationDependencies(
            source_registry=registry,
            profile_use_case=BuildProfileUseCase(registry, artifacts),
            facts=facts,
            evidence=evidence,
            artifacts=artifacts,
        )
    )


def plan_intake_use_case() -> PlanIntakeUseCase:
    registry, artifacts, _, _ = runtime_dependencies()
    return PlanIntakeUseCase(registry, artifacts)


def apply_intake_use_case() -> ApplyIntakeUseCase:
    registry, artifacts, _, _ = runtime_dependencies()
    return ApplyIntakeUseCase(registry, artifacts)


def render_output_use_case() -> RenderOutputUseCase:
    registry, _, facts, _ = runtime_dependencies()
    return RenderOutputUseCase(registry, facts)


def rebuild_wallet_inventory_use_case() -> RebuildWalletInventoryUseCase:
    _, artifacts, _, _ = runtime_dependencies()
    return RebuildWalletInventoryUseCase(artifacts)


def extract_pdf_balances_use_case() -> ExtractPdfBalancesUseCase:
    registry, artifacts, _, _ = runtime_dependencies()
    return ExtractPdfBalancesUseCase(registry, artifacts)


def initialize_workspace_use_case() -> InitializeWorkspaceUseCase:
    return InitializeWorkspaceUseCase(FilesystemWorkspaceRepository())


def configured_workspace_root() -> Path:
    return load_app_config().workspace_root
