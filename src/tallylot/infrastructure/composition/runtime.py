"""Composition-root builders for the CLI and library runtime."""

from __future__ import annotations

from pathlib import Path

from tallylot.application.checkpoints.extract_pdf_balances import (
    ExtractPdfBalancesUseCase,
)
from tallylot.application.checkpoints.rebuild_location_inventory import (
    RebuildLocationInventoryUseCase,
)
from tallylot.application.checkpoints.balance_submission import (
    ScaffoldBalanceSubmissionUseCase,
    SubmitBalancesUseCase,
)
from tallylot.application.intake.apply_intake import ApplyIntakeUseCase
from tallylot.application.intake.build_manifest import BuildManifestUseCase
from tallylot.application.intake.plan_intake import PlanIntakeUseCase
from tallylot.application.normalization.normalize_source import (
    NormalizationDependencies,
    NormalizeSourceUseCase,
)
from tallylot.application.outputs.render_output import RenderOutputUseCase
from tallylot.application.profiling.build_profile import BuildProfileUseCase
from tallylot.application.reconciliation import (
    BalanceCheckWorkflow,
    BalanceCoverageWorkflow,
    BalanceSummaryWorkflow,
)
from tallylot.application.workspace.initialize_workspace import (
    InitializeWorkspaceUseCase,
)
from tallylot.infrastructure.config import load_app_config
from tallylot.infrastructure.discovery import AdapterRegistry, build_registry
from tallylot.infrastructure.serialization import FilesystemArtifactStore
from tallylot.infrastructure.storage import (
    FilesystemEvidenceRepository,
    FilesystemFactRepository,
)
from tallylot.infrastructure.workspace import FilesystemWorkspaceRepository


def runtime_dependencies() -> tuple[
    AdapterRegistry,
    FilesystemArtifactStore,
    FilesystemFactRepository,
    FilesystemEvidenceRepository,
]:
    return (
        build_registry(),
        FilesystemArtifactStore(),
        FilesystemFactRepository(),
        FilesystemEvidenceRepository(),
    )


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


def rebuild_location_inventory_use_case() -> RebuildLocationInventoryUseCase:
    _, artifacts, _, _ = runtime_dependencies()
    return RebuildLocationInventoryUseCase(artifacts)


def extract_pdf_balances_use_case() -> ExtractPdfBalancesUseCase:
    registry, artifacts, _, _ = runtime_dependencies()
    return ExtractPdfBalancesUseCase(registry, artifacts)


def scaffold_balance_submission_use_case() -> ScaffoldBalanceSubmissionUseCase:
    _, artifacts, _, _ = runtime_dependencies()
    return ScaffoldBalanceSubmissionUseCase(artifacts)


def submit_balances_use_case() -> SubmitBalancesUseCase:
    _, artifacts, _, evidence = runtime_dependencies()
    return SubmitBalancesUseCase(evidence, artifacts)


def balance_coverage_workflow() -> BalanceCoverageWorkflow:
    _, artifacts, _, _ = runtime_dependencies()
    return BalanceCoverageWorkflow(artifacts)


def balance_check_workflow() -> BalanceCheckWorkflow:
    _, artifacts, _, evidence = runtime_dependencies()
    return BalanceCheckWorkflow(evidence, artifacts)


def balance_summary_workflow() -> BalanceSummaryWorkflow:
    _, artifacts, _, _ = runtime_dependencies()
    return BalanceSummaryWorkflow(artifacts)


def initialize_workspace_use_case() -> InitializeWorkspaceUseCase:
    return InitializeWorkspaceUseCase(FilesystemWorkspaceRepository())


def configured_workspace_root() -> Path:
    return load_app_config().workspace_root
