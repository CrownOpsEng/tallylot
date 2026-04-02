"""Ledger Live adapter."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.wallets.ledger_live.translation import translate_operations
from tallylot.adapters.sources.wallets.ledger_live.wallets import HEADER_FIELDS, extract_location_inventory
from tallylot.adapters.support import (
    match_intake_by_path_or_header,
    no_intake_route,
    passed_timezone_summary,
)
from tallylot.adapters.support.drafts import translation_batch_from_drafts
from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import AdapterId, JsonValue
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch


class LedgerLiveAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("ledger_live"),
        display_name="Ledger Live",
        version="1.0.0",
        capabilities=frozenset(
            {AdapterCapability.SOURCE_TRANSLATE, AdapterCapability.LOCATION_INVENTORY, AdapterCapability.INTAKE_ROUTE}
        ),
        description="Normalizes Ledger Live operations and extracts wallet identifiers.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "ledger" in source.lower():
            return 100
        if any(HEADER_FIELDS.issubset(set(item.header)) for item in inventory if item.header):
            return 100
        return 0

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(relative_path, facts, path_hints=("ledger",))

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="value_utc")

    def extract_location_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[LocationInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del profile
        return extract_location_inventory(source, raw_dir)

    def translate(self, profile: SourceProfile, raw_dir: Path) -> SourceTranslationBatch:
        drafts, issues = translate_operations(profile, raw_dir)
        location_inventory, _ = self.extract_location_inventory(str(profile.source), raw_dir, profile)
        return translation_batch_from_drafts(
            drafts,
            issues=issues,
            location_inventory=location_inventory,
        )


ADAPTER = LedgerLiveAdapter()
