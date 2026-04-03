"""Ronin explorer adapter."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.explorers.ronin.families import classified_csv_paths, classify_inventory_families
from tallylot.adapters.sources.explorers.ronin.translation import translate_transactions
from tallylot.adapters.support import (
    EVM_ADDRESS_PATTERN,
    IssueSpec,
    canonical_location_id_from_identifier,
    issue_record,
    location_issue,
    location_record,
    match_intake_by_path_or_header,
    no_intake_route,
    read_csv_rows,
)
from tallylot.adapters.support.drafts import translation_batch_from_drafts
from tallylot.adapters.support.locations import LocationIssueSpec, LocationRecordSpec
from tallylot.domain.issues import IssueRecord
from tallylot.domain.locations import LocationKind
from tallylot.domain.types import AdapterId, JsonValue
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from tallylot.ports.source_profiles import FileFamilyClaim, FileInventoryEntry, SourceProfile, parse_family_claim_tokens
from tallylot.ports.source_translation import SourceTranslationBatch


class _RoninAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("ronin"),
        display_name="Ronin",
        version="1.0.0",
        capabilities=frozenset(
            {AdapterCapability.SOURCE_TRANSLATE, AdapterCapability.LOCATION_INVENTORY, AdapterCapability.INTAKE_ROUTE}
        ),
        description="Normalizes Ronin explorer exports and extracts owned wallet identifiers.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        if self.classify_profile_families(source, raw_dir, inventory):
            return 100
        if "ronin" in source.lower():
            return 100
        return 0

    def classify_profile_families(
        self,
        source: str,
        raw_dir: Path,
        inventory: tuple[FileInventoryEntry, ...],
    ) -> tuple[FileFamilyClaim, ...]:
        del source, raw_dir
        return classify_inventory_families(inventory, adapter_id=self.manifest.adapter_id)

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(relative_path, facts, path_hints=("ronin",))

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        raw_files = [item for item in profile.file_inventory if _has_family(item, "explorer_export")]
        summary_files = [item for item in profile.file_inventory if _has_family(item, "action_summary")]
        if summary_files and not raw_files:
            issues = tuple(
                issue_record(
                    IssueSpec(
                        issue_id=f"ronin:{item.relative_path}:timezone_review_required",
                        source=str(profile.source),
                        adapter_id="ronin",
                        severity="high",
                        kind="timezone_review_required",
                        message=(
                            "Ronin summary exports use local wall-clock timestamps and require a companion raw "
                            "explorer export in the same capture to infer UTC timestamps."
                        ),
                        raw_file=item.relative_path,
                    )
                )
                for item in summary_files
            )
            return {
                "status": "needs_review",
                "issue_count": len(issues),
                "rows_with_dates": len(raw_files) + len(summary_files),
                "mode_counts": {"companion_inferred_local": len(summary_files)},
            }, issues
        return {
            "status": "passed",
            "issue_count": 0,
            "rows_with_dates": len(raw_files) + len(summary_files),
            "mode_counts": {
                key: value
                for key, value in {
                    "header_utc": len(raw_files),
                    "companion_inferred_local": len(summary_files),
                }.items()
                if value
            },
        }, ()

    def extract_location_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[LocationInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del profile
        addresses = sorted(_owned_addresses(raw_dir))
        issues: list[IssueRecord] = []
        if not addresses:
            return (), (
                location_issue(
                    LocationIssueSpec(
                        source=source,
                        adapter_id=str(self.manifest.adapter_id),
                        issue_kind="missing_identifier",
                        message="No Ronin wallet address could be extracted from the profiled explorer capture.",
                    )
                ),
            )
        if len(addresses) > 1:
            issues.append(
                location_issue(
                    LocationIssueSpec(
                        source=source,
                        adapter_id=str(self.manifest.adapter_id),
                        issue_kind="multiple_primary_identifiers",
                        message="The profiled Ronin capture exposed more than one owned wallet address.",
                    )
                )
            )
        evidence = tuple(
            location_record(
                LocationRecordSpec(
                    source=source,
                    location_id=canonical_location_id_from_identifier(
                        "evm_address",
                        address,
                        network_scope="ronin",
                    ),
                    location_kind=LocationKind.ADDRESS,
                    location_label=address,
                    identifier_kind="evm_address",
                    identifier_value=address,
                    network_scope="ronin",
                    controller="Ronin explorer export",
                    evidence_kind="filename",
                    evidence_path=_evidence_filename(raw_dir, address),
                    confidence="high",
                )
            )
            for address in addresses
        )
        return evidence, tuple(issues)

    def translate(self, profile: SourceProfile, raw_dir: Path) -> SourceTranslationBatch:
        location_inventory, location_issues = self.extract_location_inventory(str(profile.source), raw_dir, profile)
        drafts, issues, reviews = translate_transactions(
            profile,
            raw_dir,
            owned_addresses=_owned_addresses(raw_dir),
        )
        return translation_batch_from_drafts(
            drafts,
            issues=(*issues, *location_issues),
            reviews=reviews,
            location_inventory=location_inventory,
        )


def _owned_addresses(raw_dir: Path) -> set[str]:
    addresses: set[str] = set()
    for path, family_id in classified_csv_paths(raw_dir):
        for match in EVM_ADDRESS_PATTERN.finditer(path.name):
            addresses.add(match.group(0).lower())
        if family_id != "action_summary":
            continue
        for row in read_csv_rows(path):
            ronin_address = (row.get("RoninAddress") or "").strip().lower()
            if ronin_address.startswith("ronin:"):
                addresses.add(f"0x{ronin_address.split(':', 1)[1]}")
    return addresses


def _evidence_filename(raw_dir: Path, address: str) -> str:
    for path, _ in classified_csv_paths(raw_dir):
        if address in path.name.lower():
            return path.name
    first = classified_csv_paths(raw_dir)
    return first[0][0].name if first else ""


ADAPTER = _RoninAdapter()


def _has_family(item: FileInventoryEntry, family_id: str) -> bool:
    return any(
        adapter_id == "ronin" and claim_family_id == family_id
        for adapter_id, claim_family_id in parse_family_claim_tokens(item.family)
    )
