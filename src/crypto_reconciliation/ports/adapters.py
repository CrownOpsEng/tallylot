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

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult: ...


class OutputAdapter(Protocol):
    manifest: AdapterManifest

    def render(self, events: tuple[CanonicalEvent, ...], output_path: Path) -> RenderedArtifact: ...


class SourceAdapterRegistryPort(Protocol):
    @property
    def source_adapters(self) -> tuple[SourceAdapter, ...]: ...

    def source_adapter(self, adapter_id: str) -> SourceAdapter: ...


class OutputAdapterRegistryPort(Protocol):
    @property
    def output_adapters(self) -> tuple[OutputAdapter, ...]: ...

    def output_adapter(self, adapter_id: str) -> OutputAdapter: ...
