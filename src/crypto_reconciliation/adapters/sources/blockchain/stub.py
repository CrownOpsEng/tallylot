"""Stub blockchain adapter entry point."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    FileInventoryEntry,
    SourceProfile,
)
from crypto_reconciliation.domain.types import AdapterId
from crypto_reconciliation.ports.adapters import NormalizationResult


class BlockchainSourceStubAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("blockchain_stub"),
        display_name="Blockchain Stub",
        version="0.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE}),
        supported=False,
        description="Reserved entry point for blockchain source adapters.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del source, raw_dir, inventory
        return 0

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        del profile, raw_dir
        raise NotImplementedError(
            "Blockchain source adapters are intentionally stubbed in this phase.",
        )


ADAPTER = BlockchainSourceStubAdapter()
