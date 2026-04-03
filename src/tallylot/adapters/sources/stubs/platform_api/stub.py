"""Stub platform API adapter entry point."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import AdapterId, JsonValue
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from tallylot.ports.source_profiles import FileFamilyClaim, FileInventoryEntry, SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch


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

    def classify_profile_families(
        self,
        source: str,
        raw_dir: Path,
        inventory: tuple[FileInventoryEntry, ...],
    ) -> tuple[FileFamilyClaim, ...]:
        del source, raw_dir, inventory
        return ()

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
        raise NotImplementedError(
            "Platform API source adapters are intentionally stubbed in this phase.",
        )


ADAPTER = PlatformApiSourceStubAdapter()
