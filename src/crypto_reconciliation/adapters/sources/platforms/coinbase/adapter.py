"""Coinbase retail export adapter entry point."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.support import (
    match_intake_by_path_or_header,
    no_intake_route,
    passed_timezone_summary,
)
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

from .matching import match_coinbase_inventory
from .normalization import normalize_coinbase_exports
from .pdf_balances import extract_pdf_balances as _extract_pdf_balances
from .pdf_balances import match_pdf_statement as _match_pdf_statement


class CoinbaseAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("coinbase"),
        display_name="Coinbase",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE, AdapterCapability.INTAKE_ROUTE}),
        description="Normalizes Coinbase retail all-time exports.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        return match_coinbase_inventory(source, raw_dir, inventory)

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("coinbase",),
            header_hints=("portfolio,type,time,amount,balance,amount/balance unit",),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="value_utc")

    def extract_wallet_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()

    def match_pdf_statement(self, pdf_path: Path, text: str) -> int:
        return _match_pdf_statement(pdf_path, text)

    def extract_pdf_balances(self, pdf_path: Path, text: str) -> list[dict[str, str]]:
        return _extract_pdf_balances(text, pdf_path.name)

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        return normalize_coinbase_exports(profile, raw_dir)


ADAPTER = CoinbaseAdapter()
