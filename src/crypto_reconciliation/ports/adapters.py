"""Adapter ports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from crypto_reconciliation.domain.models import (
    AdapterManifest,
    CanonicalBalance,
    CanonicalEvent,
    FileInventoryEntry,
    IssueRecord,
    NormalizationReviewRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import JsonValue
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

from .output_workflows import BaselineArtifacts, ScreeningResult


@dataclass(frozen=True)
class NormalizationResult:
    canonical_events: tuple[CanonicalEvent, ...]
    canonical_balances: tuple[CanonicalBalance, ...]
    issues: tuple[IssueRecord, ...]
    reviews: tuple[NormalizationReviewRecord, ...]
    wallet_inventory: tuple[WalletInventoryRecord, ...]


@dataclass(frozen=True)
class RenderedArtifact:
    path: Path
    row_count: int
    metadata: dict[str, str]


class SourceAdapter(Protocol):
    manifest: AdapterManifest

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int: ...

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]: ...

    def extract_wallet_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]: ...

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult: ...


class OutputAdapter(Protocol):
    manifest: AdapterManifest

    def render(self, events: tuple[CanonicalEvent, ...], output_path: Path) -> RenderedArtifact: ...

    def candidate_artifact_name(self) -> str: ...

    def match_candidate(self, candidate_path: Path, artifacts: ArtifactStorePort) -> int: ...

    def screen_candidate(
        self,
        candidate_path: Path,
        baseline_export_dir: Path,
        artifacts: ArtifactStorePort,
    ) -> ScreeningResult: ...

    def match_baseline_exports(self, export_dir: Path, artifacts: ArtifactStorePort) -> int: ...

    def build_baseline_artifacts(self, export_dir: Path, artifacts: ArtifactStorePort) -> BaselineArtifacts: ...


class SourceAdapterRegistryPort(Protocol):
    @property
    def source_adapters(self) -> tuple[SourceAdapter, ...]: ...

    def source_adapter(self, adapter_id: str) -> SourceAdapter: ...


class OutputAdapterRegistryPort(Protocol):
    @property
    def output_adapters(self) -> tuple[OutputAdapter, ...]: ...

    def output_adapter(self, adapter_id: str) -> OutputAdapter: ...
