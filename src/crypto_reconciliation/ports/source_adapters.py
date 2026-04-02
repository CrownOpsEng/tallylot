"""Source adapter ports."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from crypto_reconciliation.domain.issues import IssueRecord
from crypto_reconciliation.domain.types import JsonValue
from crypto_reconciliation.ports.adapter_contracts import AdapterManifest
from crypto_reconciliation.ports.evidence import WalletInventoryRecord
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from crypto_reconciliation.ports.source_profiles import FileInventoryEntry, SourceProfile
from crypto_reconciliation.ports.source_translation import SourceTranslationBatch


class SourceAdapter(Protocol):
    manifest: AdapterManifest

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int: ...

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int: ...

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None: ...

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

    def translate(self, profile: SourceProfile, raw_dir: Path) -> SourceTranslationBatch: ...


class SourceAdapterRegistryPort(Protocol):
    @property
    def source_adapters(self) -> tuple[SourceAdapter, ...]: ...

    def source_adapter(self, adapter_id: str) -> SourceAdapter: ...
