"""EVM explorer adapter."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.explorers.evm_explorer.families import (
    classify_inventory_families,
)
from tallylot.adapters.sources.explorers.evm_explorer.portfolio_evidence import (
    extract_portfolio_balance_references,
)
from tallylot.adapters.sources.explorers.evm_explorer.translation import (
    translate_transactions,
)
from tallylot.adapters.support import (
    EVM_ADDRESS_PATTERN,
    location_issue,
    location_record,
    match_intake_by_path_or_header,
    matching_file_paths,
    no_intake_route,
    passed_timezone_summary,
    read_csv_rows,
    location_id_from_identifier,
)
from tallylot.adapters.support.drafts import (
    TranslationBatchDrafts,
    translation_batch_from_drafts,
)
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

TRANSACTION_HEADER_FIELDS = {"Transaction Hash", "DateTime (UTC)"}


class _EvmExplorerAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("evm_explorer"),
        display_name="EVM Explorer",
        version="1.0.0",
        capabilities=frozenset(
            {
                AdapterCapability.SOURCE_TRANSLATE,
                AdapterCapability.LOCATION_INVENTORY,
                AdapterCapability.INTAKE_ROUTE,
            }
        ),
        description="Normalizes EVM explorer exports and extracts owned EVM addresses.",
    )

    def match(
        self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]
    ) -> int:
        if self.classify_profile_families(source, raw_dir, inventory):
            return 100
        lower_source = source.lower()
        if "explorer" in lower_source or any(
            chain in lower_source for chain in ("bsc", "ethereum", "polygon", "arb")
        ):
            return 100
        if any(
            TRANSACTION_HEADER_FIELDS.issubset(set(item.header))
            for item in inventory
            if item.header
        ):
            return 75
        if any("explorer" in item.relative_path.lower() for item in inventory):
            return 75
        return 0

    def classify_profile_families(
        self,
        source: str,
        raw_dir: Path,
        inventory: tuple[FileInventoryEntry, ...],
    ) -> tuple[FileFamilyClaim, ...]:
        del source, raw_dir
        return classify_inventory_families(
            inventory, adapter_id=self.manifest.adapter_id
        )

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("etherscan", "arbiscan", "polygonscan", "bsc", "evm"),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="header_utc")

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
                        message="No EVM address could be extracted from the profiled explorer capture.",
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
                        message="The profiled explorer capture exposed more than one owned EVM address.",
                    )
                )
            )
        evidence = tuple(
            location_record(
                LocationRecordSpec(
                    source=source,
                    location_id=location_id_from_identifier(
                        "evm_address",
                        address,
                        network_scope=_network_scope(source),
                    ),
                    location_kind=LocationKind.ADDRESS,
                    location_label=address,
                    identifier_kind="evm_address",
                    identifier_value=address,
                    network_scope=_network_scope(source),
                    controller="Explorer export",
                    evidence_kind="filename",
                    evidence_provenance=ProvenanceLocator.from_reference_ref(
                        _evidence_filename(raw_dir, address)
                    ),
                    confidence="high",
                )
            )
            for address in addresses
        )
        return evidence, tuple(issues)

    def translate(
        self, profile: SourceProfile, raw_dir: Path
    ) -> SourceTranslationBatch:
        location_inventory, location_issues = self.extract_location_inventory(
            str(profile.source), raw_dir, profile
        )
        drafts, issues = translate_transactions(
            profile,
            raw_dir,
            owned_addresses=_owned_addresses(raw_dir),
            network_scope=_network_scope(str(profile.source)),
        )
        balance_references, evidence_issues, evidence_reviews = (
            extract_portfolio_balance_references(
                profile,
                raw_dir,
                location_inventory=location_inventory,
                network_scope=_network_scope(str(profile.source)),
            )
        )
        return translation_batch_from_drafts(
            TranslationBatchDrafts(
                drafts=drafts,
                balance_references=balance_references,
                balance_reference_issues=evidence_issues,
                issues=(*issues, *location_issues),
                reviews=evidence_reviews,
                location_inventory=location_inventory,
            )
        )


def _owned_addresses(raw_dir: Path) -> set[str]:
    addresses: set[str] = set()
    for path in matching_file_paths(raw_dir):
        for match in EVM_ADDRESS_PATTERN.finditer(path.name):
            addresses.add(match.group(0).lower())
    if addresses:
        return addresses
    for path in matching_file_paths(raw_dir):
        rows = read_csv_rows(path)
        to_addresses = {
            (row.get("To") or "").strip().lower()
            for row in rows
            if EVM_ADDRESS_PATTERN.fullmatch((row.get("To") or "").strip())
        }
        if len(to_addresses) == 1:
            return to_addresses
    return set()


def _network_scope(source: str) -> str:
    lower_source = source.lower()
    if "bsc" in lower_source:
        return "bsc"
    if "polygon" in lower_source:
        return "polygon"
    if "arb" in lower_source:
        return "arbitrum"
    return "ethereum"


def _evidence_filename(raw_dir: Path, address: str) -> str:
    for path in matching_file_paths(raw_dir):
        if address in path.name.lower():
            return path.name
    first = matching_file_paths(raw_dir)
    return first[0].name if first else ""


ADAPTER = _EvmExplorerAdapter()
