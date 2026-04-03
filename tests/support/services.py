from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from crypto_reconciliation.application.services.normalize import (
    NormalizationDependencies,
    NormalizationService,
)
from crypto_reconciliation.application.services.profile import ProfileService
from crypto_reconciliation.application.services.render import OutputRenderService
from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    FileInventoryEntry,
    IssueRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, JsonValue, SourceId
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from crypto_reconciliation.infrastructure.storage import FilesystemStorage
from crypto_reconciliation.ports.adapters import NormalizationResult, SourceAdapter, SourceAdapterRegistryPort


def build_source_profile(
    *,
    source: str = "fixture_source",
    adapter_id: str,
    raw_dir: str = "/tmp/raw",
    normalization_hints: dict[str, JsonValue] | None = None,
) -> SourceProfile:
    return SourceProfile(
        source=SourceId(source),
        raw_dir=raw_dir,
        adapter_id=AdapterId(adapter_id),
        manifest_fingerprint="fixture-fingerprint",
        file_inventory=(),
        supported=True,
        normalization_hints=normalization_hints or {},
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
) -> OutputRenderService:
    runtime_registry = build_registry()
    return OutputRenderService(runtime_registry, artifacts or FilesystemArtifactStore())


@dataclass(frozen=True)
class FakeSourceRegistry:
    source_adapters: tuple[SourceAdapter, ...]

    def source_adapter(self, adapter_id: str) -> SourceAdapter:
        for adapter in self.source_adapters:
            if str(adapter.manifest.adapter_id) == adapter_id:
                return adapter
        raise KeyError(adapter_id)


class MatchingSourceAdapter:
    def __init__(self, adapter_id: str, *, supported: bool = True) -> None:
        self.manifest = AdapterManifest(
            adapter_id=AdapterId(adapter_id),
            display_name=adapter_id,
            version="1.0.0",
            capabilities=frozenset({AdapterCapability.NORMALIZE}),
            supported=supported,
        )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del source, raw_dir, inventory
        return 100

    def normalize(self, profile: object, raw_dir: Path) -> NormalizationResult:
        del profile, raw_dir
        raise AssertionError("normalize should not be called in this test")

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        del profile
        return {}, ()

    def extract_wallet_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()


def build_registry_backed_normalization_service(
    *,
    registry: SourceAdapterRegistryPort,
    artifacts: FilesystemArtifactStore,
) -> NormalizationService:
    runtime_registry = build_registry()
    return NormalizationService(
        NormalizationDependencies(
            source_registry=registry,
            output_registry=runtime_registry,
            profile_service=ProfileService(registry, artifacts),
            storage=FilesystemStorage(),
            artifacts=artifacts,
        )
    )
