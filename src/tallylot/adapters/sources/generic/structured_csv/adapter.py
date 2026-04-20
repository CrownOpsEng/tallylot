"""Structured CSV source adapter entry point."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from tallylot.domain.issues import IssueRecord
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

from .contracts import REQUIRED_HEADER
from .normalization import translate_structured_csv


class _StructuredCsvSourceAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("structured_csv"),
        display_name="Structured CSV",
        version="1.0.0",
        capabilities=frozenset(
            {AdapterCapability.SOURCE_TRANSLATE, AdapterCapability.LOCATION_INVENTORY}
        ),
        description="Normalizes a strongly typed structured CSV source capture.",
    )

    def match(
        self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]
    ) -> int:
        del source, raw_dir
        for item in inventory:
            if (
                item.relative_path == "transactions.csv"
                and item.header == REQUIRED_HEADER
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
                family_id="structured_transactions",
            )
            for item in inventory
            if item.relative_path == "transactions.csv"
            and item.header == REQUIRED_HEADER
        )

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
        summary: dict[str, JsonValue] = {
            "status": "needs_review",
            "issue_count": 0,
            "rows_with_dates": 1,
            "mode_counts": {"naive": 1},
        }
        return summary, ()

    def extract_location_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[LocationInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir
        result = self.translate(profile, Path(profile.raw_dir))
        return result.location_inventory, ()

    def translate(
        self, profile: SourceProfile, raw_dir: Path
    ) -> SourceTranslationBatch:
        return translate_structured_csv(
            profile,
            raw_dir,
            adapter_id=str(self.manifest.adapter_id),
        )


ADAPTER = _StructuredCsvSourceAdapter()
