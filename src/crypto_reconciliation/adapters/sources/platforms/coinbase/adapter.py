"""Coinbase retail export adapter entry point."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.support import (
    IssueSpec,
    issue_record,
    match_intake_by_path_or_header,
    no_intake_route,
    passed_timezone_summary,
)
from crypto_reconciliation.adapters.support.drafts import EconomicActivityDraft, normalization_result_from_drafts
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

from .asset_migrations import normalize_asset_migration as _normalize_asset_migration
from .matching import match_coinbase_inventory
from .matching import retail_path as _retail_path
from .pdf_balances import extract_pdf_balances as _extract_pdf_balances
from .pdf_balances import match_pdf_statement as _match_pdf_statement
from .retail_csv import read_retail_rows as _read_retail_rows
from .retail_rows import normalize_retail_row as _normalize_row


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
        retail_path = _retail_path(raw_dir)
        if retail_path is None:
            return normalization_result_from_drafts(
                issues=(
                    issue_record(
                        IssueSpec(
                            source=str(profile.source),
                            adapter_id=str(self.manifest.adapter_id),
                            issue_id="coinbase:missing_retail_csv",
                            kind="missing_required_input",
                            message="Coinbase retail all-time CSV is required for deterministic normalization.",
                            severity="high",
                        )
                    ),
                ),
            )

        drafts: list[EconomicActivityDraft] = []
        issues: list[IssueRecord] = []
        asset_migrations: dict[str, list[dict[str, str]]] = {}
        for index, row in enumerate(_read_retail_rows(retail_path), start=2):
            row_id = (row.get("ID") or "").strip()
            tx_type = (row.get("Transaction Type") or "").strip().lower()
            if tx_type == "asset migration":
                timestamp = (row.get("Timestamp") or "").strip()
                asset_migrations.setdefault(timestamp, []).append(row)
                continue
            try:
                drafts.append(_normalize_row(profile, retail_path.name, row))
            except ValueError as error:
                issues.append(
                    issue_record(
                        IssueSpec(
                            source=str(profile.source),
                            adapter_id=str(self.manifest.adapter_id),
                            issue_id=f"coinbase:{retail_path.name}:{row_id or tx_type or 'row'}",
                            kind="unsupported_row",
                            message=str(error),
                            raw_file=retail_path.name,
                            raw_row_ref=f"row:{index}",
                        )
                    )
                )
        for timestamp, rows in sorted(asset_migrations.items()):
            try:
                drafts.append(_normalize_asset_migration(profile, retail_path.name, timestamp, rows))
            except ValueError as error:
                issues.append(
                    issue_record(
                        IssueSpec(
                            source=str(profile.source),
                            adapter_id=str(self.manifest.adapter_id),
                            issue_id=f"coinbase:{retail_path.name}:asset_migration:{timestamp}",
                            kind="unsupported_row",
                            message=str(error),
                            raw_file=retail_path.name,
                            raw_row_ref=timestamp,
                        )
                    )
                )
        return normalization_result_from_drafts(
            drafts,
            issues=issues,
        )


ADAPTER = CoinbaseAdapter()
