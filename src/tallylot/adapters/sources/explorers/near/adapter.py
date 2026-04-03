"""NEAR export adapter."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.explorers.near.translation import translate_transactions
from tallylot.adapters.support import (
    location_id_from_parts,
    location_record,
    match_intake_by_path_or_header,
    no_intake_route,
    passed_timezone_summary,
)
from tallylot.adapters.support.drafts import translation_batch_from_drafts
from tallylot.adapters.support.locations import LocationRecordSpec
from tallylot.domain.issues import IssueRecord
from tallylot.domain.locations import LocationKind
from tallylot.domain.types import AdapterId, JsonValue
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch


class NearAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("near"),
        display_name="NEAR",
        version="1.0.0",
        capabilities=frozenset(
            {AdapterCapability.SOURCE_TRANSLATE, AdapterCapability.LOCATION_INVENTORY, AdapterCapability.INTAKE_ROUTE}
        ),
        description="Normalizes NEAR transaction exports and extracts wallet identifiers.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "near" in source.lower():
            return 100
        if any(item.relative_path.endswith("_transactions.csv") for item in inventory):
            return 100
        return 0

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(relative_path, facts, path_hints=("near",))

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="naive")

    def extract_location_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[LocationInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del profile
        evidence: list[LocationInventoryRecord] = []
        for path in sorted(raw_dir.glob("*_transactions.csv")):
            identifier = path.name.removesuffix("_transactions.csv")
            evidence.append(
                location_record(
                    LocationRecordSpec(
                        source=source,
                        location_id=location_id_from_parts(source, "account", identifier),
                        location_kind=LocationKind.ACCOUNT,
                        location_label=identifier,
                        identifier_kind="near_account",
                        identifier_value=identifier,
                        network_scope="near",
                        controller="NearBlocks export",
                        evidence_kind="filename",
                        evidence_path=path.name,
                        confidence="high",
                    )
                )
            )
        return tuple(evidence), ()

    def translate(self, profile: SourceProfile, raw_dir: Path) -> SourceTranslationBatch:
        drafts, issues = translate_transactions(profile, raw_dir)
        location_inventory, _ = self.extract_location_inventory(str(profile.source), raw_dir, profile)
        return translation_batch_from_drafts(
            drafts,
            issues=issues,
            location_inventory=location_inventory,
        )


ADAPTER = NearAdapter()
