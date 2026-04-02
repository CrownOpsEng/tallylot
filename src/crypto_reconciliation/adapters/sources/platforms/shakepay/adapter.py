"""Shakepay export adapter."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.sources.platforms.shakepay.pdf_balances import (
    extract_pdf_balances as _extract_pdf_balances,
)
from crypto_reconciliation.adapters.sources.platforms.shakepay.pdf_balances import (
    match_pdf_statement as _match_pdf_statement,
)
from crypto_reconciliation.adapters.sources.platforms.shakepay.translation import translate_row
from crypto_reconciliation.adapters.support import (
    collect_csv_row_results,
    match_intake_by_path_or_header,
    no_intake_route,
    passed_timezone_summary,
)
from crypto_reconciliation.adapters.support.drafts import normalization_result_from_drafts
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


class ShakepayAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("shakepay"),
        display_name="Shakepay",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE, AdapterCapability.INTAKE_ROUTE}),
        description="Normalizes Shakepay cash and crypto export summaries.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "shakepay" in source.lower():
            return 100
        if any("crypto_transactions_summary.csv" in item.relative_path for item in inventory):
            return 100
        return 0

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("shakepay", "crypto_transactions_summary.csv", "cash_transactions_summary.csv"),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="america_toronto")

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
        drafts, issues = collect_csv_row_results(raw_dir, lambda row_context: translate_row(profile, row_context))
        return normalization_result_from_drafts(
            drafts,
            issues=issues,
        )


ADAPTER = ShakepayAdapter()
