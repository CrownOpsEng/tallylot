"""Runtime dependency builders for the CLI."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.services import NormalizationService, OutputProjectionService, ProfileService
from crypto_reconciliation.application.services.normalize import NormalizationDependencies
from crypto_reconciliation.infrastructure.config import load_app_config
from crypto_reconciliation.infrastructure.discovery import AdapterRegistry, build_registry
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore
from crypto_reconciliation.infrastructure.storage import FilesystemStorage


def runtime_dependencies() -> tuple[AdapterRegistry, FilesystemArtifactStore, FilesystemStorage]:
    return build_registry(), FilesystemArtifactStore(), FilesystemStorage()


def profile_service() -> ProfileService:
    registry, artifacts, _ = runtime_dependencies()
    return ProfileService(registry, artifacts)


def normalization_service() -> NormalizationService:
    registry, artifacts, storage = runtime_dependencies()
    return NormalizationService(
        NormalizationDependencies(
            source_registry=registry,
            profile_service=ProfileService(registry, artifacts),
            storage=storage,
            artifacts=artifacts,
        )
    )


def render_service() -> OutputProjectionService:
    registry, artifacts, _ = runtime_dependencies()
    return OutputProjectionService(registry, artifacts)


def configured_workspace_root() -> Path:
    return load_app_config().workspace_root
