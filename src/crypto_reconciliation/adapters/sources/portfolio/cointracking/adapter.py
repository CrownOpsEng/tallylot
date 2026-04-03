"""CoinTracking portfolio intake adapter entry point."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    FileInventoryEntry,
    IssueRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, JsonValue
from crypto_reconciliation.ports.adapters import NormalizationResult
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest

from .routing import match_intake as match_portfolio_intake
from .routing import route_intake as route_portfolio_intake


class CoinTrackingPortfolioAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("cointracking_portfolio"),
        display_name="CoinTracking Portfolio",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.INTAKE_ROUTE}),
        description="Routes CoinTracking HTML, PDF, and sidecar portfolio exports during intake.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del source, raw_dir, inventory
        return 0

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
        return {"status": "passed", "issue_count": 0, "rows_with_dates": 0, "mode_counts": {}}, ()

    def extract_wallet_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        del profile, raw_dir
        raise NotImplementedError("CoinTracking portfolio intake is intentionally intake-only in this phase.")


ADAPTER = CoinTrackingPortfolioAdapter()
