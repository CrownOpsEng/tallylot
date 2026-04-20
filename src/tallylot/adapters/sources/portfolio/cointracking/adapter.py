"""CoinTracking portfolio intake adapter entry point."""

from __future__ import annotations

from pathlib import Path

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

from .routing import match_intake as match_portfolio_intake
from .routing import route_intake as route_portfolio_intake


class _CoinTrackingPortfolioAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("cointracking_portfolio"),
        display_name="CoinTracking Portfolio",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.INTAKE_ROUTE}),
        description="Routes CoinTracking HTML, PDF, and sidecar portfolio exports during intake.",
    )

    def match(
        self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]
    ) -> int:
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
        del facts
        return match_portfolio_intake(relative_path)

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return route_portfolio_intake(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        del profile
        return {
            "status": "passed",
            "issue_count": 0,
            "rows_with_dates": 0,
            "mode_counts": {},
        }, ()

    def extract_location_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[LocationInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()

    def translate(
        self, profile: SourceProfile, raw_dir: Path
    ) -> SourceTranslationBatch:
        del profile, raw_dir
        raise NotImplementedError(
            "CoinTracking portfolio intake is intentionally intake-only in this phase."
        )


ADAPTER = _CoinTrackingPortfolioAdapter()
