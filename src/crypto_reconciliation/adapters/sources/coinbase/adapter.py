"""Coinbase retail export adapter entry point."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.sources.mapped_event_support import NormalizationIssueSpec, normalization_issue
from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    CanonicalEvent,
    FileInventoryEntry,
    IssueRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, JsonValue
from crypto_reconciliation.ports.adapters import NormalizationResult

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
        capabilities=frozenset({AdapterCapability.NORMALIZE}),
        description="Normalizes Coinbase retail all-time exports.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        return match_coinbase_inventory(source, raw_dir, inventory)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        rows_with_dates = sum(1 for item in profile.file_inventory if item.date_field)
        return {
            "status": "passed",
            "issue_count": 0,
            "rows_with_dates": rows_with_dates,
            "mode_counts": {"value_utc": rows_with_dates} if rows_with_dates else {},
        }, ()

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
            return NormalizationResult(
                canonical_events=(),
                canonical_balances=(),
                issues=(
                    normalization_issue(
                        NormalizationIssueSpec(
                            source=str(profile.source),
                            adapter_id=str(self.manifest.adapter_id),
                            issue_id="coinbase:missing_retail_csv",
                            kind="missing_required_input",
                            message="Coinbase retail all-time CSV is required for deterministic normalization.",
                            severity="high",
                        )
                    ),
                ),
                reviews=(),
                wallet_inventory=(),
            )

        events: list[CanonicalEvent] = []
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
                event = _normalize_row(profile, retail_path.name, row)
            except ValueError as error:
                issues.append(
                    normalization_issue(
                        NormalizationIssueSpec(
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
                continue
            events.append(event)
        for timestamp, rows in sorted(asset_migrations.items()):
            try:
                events.append(_normalize_asset_migration(profile, retail_path.name, timestamp, rows))
            except ValueError as error:
                issues.append(
                    normalization_issue(
                        NormalizationIssueSpec(
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
        return NormalizationResult(
            canonical_events=tuple(events),
            canonical_balances=(),
            issues=tuple(issues),
            reviews=(),
            wallet_inventory=(),
        )


ADAPTER = CoinbaseAdapter()
