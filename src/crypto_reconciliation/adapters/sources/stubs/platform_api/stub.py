"""Stub platform API adapter entry point."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from crypto_reconciliation.domain.issues import IssueRecord
from crypto_reconciliation.domain.types import AdapterId, JsonValue
from crypto_reconciliation.ports.adapter_contracts import AdapterCapability, AdapterManifest
from crypto_reconciliation.ports.evidence import WalletInventoryRecord
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from crypto_reconciliation.ports.source_profiles import FileInventoryEntry, SourceProfile
from crypto_reconciliation.ports.source_translation import SourceTranslationBatch


class PlatformApiSourceStubAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("platform_api_stub"),
        display_name="Platform API Stub",
        version="0.0.0",
        capabilities=frozenset({AdapterCapability.SOURCE_TRANSLATE}),
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

    def translate(self, profile: SourceProfile, raw_dir: Path) -> SourceTranslationBatch:
        del profile, raw_dir
        raise NotImplementedError(
            "Platform API source adapters are intentionally stubbed in this phase.",
        )


ADAPTER = PlatformApiSourceStubAdapter()
