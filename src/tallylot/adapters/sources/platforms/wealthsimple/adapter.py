"""Wealthsimple crypto export adapter."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.wealthsimple.translation import (
    ACTIVITY_HEADER,
    BROKER_HEADER,
    normalize_row,
    skip_unrecognized_csv,
)
from tallylot.adapters.support import (
    collect_csv_row_results,
    match_intake_by_path_or_header,
    no_intake_route,
    passed_timezone_summary,
    skip_files_outside_profile_families,
)
from tallylot.adapters.support.drafts import translation_batch_from_drafts
from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import AdapterId, JsonValue
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from tallylot.ports.source_profiles import FileFamilyClaim, FileInventoryEntry, SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch


class WealthsimpleAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("wealthsimple"),
        display_name="Wealthsimple",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.SOURCE_TRANSLATE, AdapterCapability.INTAKE_ROUTE}),
        description="Normalizes Wealthsimple crypto activity exports.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "wealthsimple" in source.lower():
            return 100
        if any(item.header in {BROKER_HEADER, ACTIVITY_HEADER} for item in inventory):
            return 100
        return 0

    def classify_profile_families(
        self,
        source: str,
        raw_dir: Path,
        inventory: tuple[FileInventoryEntry, ...],
    ) -> tuple[FileFamilyClaim, ...]:
        del source, raw_dir
        return tuple(
            FileFamilyClaim(
                relative_path=item.relative_path,
                adapter_id=self.manifest.adapter_id,
                family_id="broker_activity" if item.header == BROKER_HEADER else "wallet_activity",
            )
            for item in inventory
            if item.header in {BROKER_HEADER, ACTIVITY_HEADER}
        )

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("wealthsimple",),
            header_hints=(",".join(BROKER_HEADER).lower(), ",".join(ACTIVITY_HEADER).lower()),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="date_only")

    def extract_location_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[LocationInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()

    def translate(self, profile: SourceProfile, raw_dir: Path) -> SourceTranslationBatch:
        drafts, issues = collect_csv_row_results(
            raw_dir,
            lambda row_context: normalize_row(profile, row_context),
            skip_file=skip_files_outside_profile_families(
                raw_dir,
                profile,
                family_ids=("broker_activity", "wallet_activity"),
                extra_skip=skip_unrecognized_csv,
            ),
        )
        return translation_batch_from_drafts(
            drafts,
            issues=issues,
        )


ADAPTER = WealthsimpleAdapter()
