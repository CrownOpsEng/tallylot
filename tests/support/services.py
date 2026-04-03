from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tallylot.application.normalization import NormalizationDependencies, NormalizeSourceUseCase
from tallylot.application.outputs import RenderOutputUseCase
from tallylot.application.profiling import BuildProfileUseCase
from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import AdapterId, JsonValue, SourceId
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization import FilesystemArtifactStore
from tallylot.infrastructure.storage import FilesystemEvidenceRepository, FilesystemFactRepository
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from tallylot.ports.source_adapters import SourceAdapter, SourceAdapterRegistryPort
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch


def build_source_profile(
    *,
    adapter_id: str,
    source: str = "fixture",
    raw_dir: str = "/tmp/raw",
    **profile_fields: Any,
) -> SourceProfile:
    metadata = profile_fields.pop("metadata", {})
    normalization_hints = profile_fields.pop("normalization_hints", {})
    timezone_summary = profile_fields.pop("timezone_summary", {})
    return SourceProfile(
        source=SourceId(source),
        raw_dir=raw_dir,
        adapter_id=AdapterId(adapter_id),
        manifest_fingerprint="fixture",
        file_inventory=(),
        supported=True,
        metadata=metadata,
        normalization_hints=normalization_hints,
        timezone_summary=timezone_summary,
        **profile_fields,
    )


def build_profile_service(
    *,
    artifacts: FilesystemArtifactStore | None = None,
) -> BuildProfileUseCase:
    runtime_registry = build_registry()
    return BuildProfileUseCase(runtime_registry, artifacts or FilesystemArtifactStore())


def build_normalization_service(
    *,
    artifacts: FilesystemArtifactStore | None = None,
    registry: SourceAdapterRegistryPort | None = None,
) -> NormalizeSourceUseCase:
    runtime_registry = build_registry() if registry is None else registry
    resolved_artifacts = artifacts or FilesystemArtifactStore()
    return NormalizeSourceUseCase(
        NormalizationDependencies(
            source_registry=runtime_registry,
            profile_use_case=BuildProfileUseCase(runtime_registry, resolved_artifacts),
            facts=FilesystemFactRepository(),
            evidence=FilesystemEvidenceRepository(),
            artifacts=resolved_artifacts,
        )
    )


def build_registry_backed_normalization_service(
    *,
    artifacts: FilesystemArtifactStore | None = None,
    registry: SourceAdapterRegistryPort,
) -> NormalizeSourceUseCase:
    return build_normalization_service(artifacts=artifacts, registry=registry)


def build_render_service() -> RenderOutputUseCase:
    runtime_registry = build_registry()
    return RenderOutputUseCase(runtime_registry, FilesystemFactRepository())


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
            capabilities=frozenset({AdapterCapability.SOURCE_TRANSLATE}),
            supported=supported,
        )

    def match(self, source: str, raw_dir: Path, inventory: tuple[object, ...]) -> int:
        del source, raw_dir, inventory
        return 100

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        del relative_path, facts
        return 0

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        del request
        route: IntakeRoute | None = None
        return route

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        del profile
        return {}, ()

    def extract_location_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[LocationInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()

    def translate(self, profile: SourceProfile, raw_dir: Path) -> SourceTranslationBatch:
        del profile, raw_dir
        raise AssertionError("translate should not be called in this test")
