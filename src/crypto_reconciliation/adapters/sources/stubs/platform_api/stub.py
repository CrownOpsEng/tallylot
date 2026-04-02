"""Stub platform API adapter entry point."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    FileInventoryEntry,
    IssueRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, JsonValue
from crypto_reconciliation.ports.adapters import NormalizationResult
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest


class PlatformApiSourceStubAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("platform_api_stub"),
        display_name="Platform API Stub",
        version="0.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE}),
        supported=False,
        description="Reserved entry point for platform API source adapters.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del source, raw_dir, inventory
        return 0

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        del relative_path, facts
        return 0

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        del request
        return cast(IntakeRoute | None, None)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        del profile
        return {"status": "passed", "issue_count": 0, "rows_with_dates": 0, "mode_counts": {}}, ()

    def extract_wallet_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        del profile, raw_dir
        raise NotImplementedError(
            "Platform API source adapters are intentionally stubbed in this phase.",
        )


ADAPTER = PlatformApiSourceStubAdapter()
