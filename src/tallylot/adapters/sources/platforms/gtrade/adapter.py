"""GTrade report adapter."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.gtrade.translation import (
    translate_transactions,
)
from tallylot.adapters.support import (
    location_id_from_parts,
    location_issue,
    location_record,
    match_intake_by_path_or_header,
    matching_file_paths,
    no_intake_route,
    passed_timezone_summary,
    read_csv_header,
    read_csv_rows,
)
from tallylot.adapters.support.drafts import translation_batch_from_drafts
from tallylot.adapters.support.locations import LocationIssueSpec, LocationRecordSpec
from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.issues import IssueRecord
from tallylot.domain.locations import LocationKind
from tallylot.domain.types import AdapterId, JsonValue
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.intake_routing import (
    IntakeFileFacts,
    IntakeRoute,
    IntakeRoutingRequest,
)
from tallylot.ports.source_profiles import (
    FileFamilyClaim,
    FileInventoryEntry,
    SourceProfile,
)
from tallylot.ports.source_translation import SourceTranslationBatch


class _GTradeAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("gtrade"),
        display_name="GTrade",
        version="1.0.0",
        capabilities=frozenset(
            {
                AdapterCapability.SOURCE_TRANSLATE,
                AdapterCapability.LOCATION_INVENTORY,
                AdapterCapability.INTAKE_ROUTE,
            }
        ),
        description="Normalizes GTrade realized PnL reports and extracts trader aliases.",
    )

    def match(
        self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]
    ) -> int:
        del raw_dir
        if "gtrade" in source.lower():
            return 100
        if any(
            item.header[:3] == ("DATE", "PAIR", "ADDR")
            for item in inventory
            if item.header
        ):
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
                family_id="realized_pnl_report",
            )
            for item in inventory
            if item.header[:3] == ("DATE", "PAIR", "ADDR")
        )

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path, facts, path_hints=("gtrade",)
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
        del profile
        evidence: list[LocationInventoryRecord] = []
        issues: list[IssueRecord] = []
        for path in matching_file_paths(raw_dir):
            if _skip_unrecognized_csv(path):
                continue
            for row in read_csv_rows(path):
                alias = (row.get("ADDR") or "").strip().lower()
                if not alias:
                    continue
                evidence.append(
                    location_record(
                        LocationRecordSpec(
                            source=source,
                            location_id=location_id_from_parts(source, "alias", alias),
                            location_kind=LocationKind.OTHER,
                            location_label=alias,
                            identifier_kind="address_alias",
                            identifier_value=alias,
                            network_scope="polygon",
                            controller="GTrade report",
                            evidence_kind="csv_row",
                            evidence_provenance=ProvenanceLocator.from_reference_ref(
                                path.name
                            ),
                            confidence="medium",
                            note="The report exposes a truncated trader alias instead of a full on-chain address.",
                        )
                    )
                )
                issues.append(
                    location_issue(
                        LocationIssueSpec(
                            source=source,
                            adapter_id=str(self.manifest.adapter_id),
                            issue_kind="partial_identifier_only",
                            message=(
                                "GTrade evidence exposes only a truncated address alias; keep companion explorer "
                                "evidence linked in the wallet inventory."
                            ),
                            location_id=str(
                                location_id_from_parts(source, "alias", alias)
                            ),
                            raw_file=path.name,
                        )
                    )
                )
                break
        if not evidence:
            issues.append(
                location_issue(
                    LocationIssueSpec(
                        source=source,
                        adapter_id=str(self.manifest.adapter_id),
                        issue_kind="missing_identifier",
                        message="No address alias was found in the GTrade report.",
                    )
                )
            )
        return tuple(evidence), tuple(issues)

    def translate(
        self, profile: SourceProfile, raw_dir: Path
    ) -> SourceTranslationBatch:
        location_inventory, _ = self.extract_location_inventory(
            str(profile.source), raw_dir, profile
        )
        drafts, issues = translate_transactions(profile, raw_dir)
        return translation_batch_from_drafts(
            drafts,
            issues=issues,
            location_inventory=location_inventory,
        )


def _skip_unrecognized_csv(path: Path) -> bool:
    header = read_csv_header(path)
    return header[:3] != ("DATE", "PAIR", "ADDR")


ADAPTER = _GTradeAdapter()
