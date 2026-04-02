from __future__ import annotations

from crypto_reconciliation.application.services.normalize import (
    NormalizationDependencies,
    NormalizationService,
)
from crypto_reconciliation.application.services.profile import ProfileService
from crypto_reconciliation.application.services.render import CoinTrackingRenderService
from crypto_reconciliation.domain.models import SourceProfile
from crypto_reconciliation.domain.types import AdapterId, SourceId
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from crypto_reconciliation.infrastructure.storage import FilesystemStorage


def build_source_profile(
    *,
    source: str = "fixture_source",
    adapter_id: str,
    raw_dir: str = "/tmp/raw",
) -> SourceProfile:
    return SourceProfile(
        source=SourceId(source),
        raw_dir=raw_dir,
        adapter_id=AdapterId(adapter_id),
        manifest_fingerprint="fixture-fingerprint",
        file_inventory=(),
        supported=True,
    )


def build_profile_service(
    *,
    artifacts: FilesystemArtifactStore | None = None,
) -> ProfileService:
    runtime_registry = build_registry()
    return ProfileService(runtime_registry, artifacts or FilesystemArtifactStore())


def build_normalization_service(
    *,
    artifacts: FilesystemArtifactStore | None = None,
) -> NormalizationService:
    runtime_registry = build_registry()
    resolved_artifacts = artifacts or FilesystemArtifactStore()
    return NormalizationService(
        NormalizationDependencies(
            source_registry=runtime_registry,
            output_registry=runtime_registry,
            profile_service=ProfileService(runtime_registry, resolved_artifacts),
            storage=FilesystemStorage(),
            artifacts=resolved_artifacts,
        )
    )


def build_render_service(
    *,
    artifacts: FilesystemArtifactStore | None = None,
) -> CoinTrackingRenderService:
    runtime_registry = build_registry()
    return CoinTrackingRenderService(runtime_registry, artifacts or FilesystemArtifactStore())
