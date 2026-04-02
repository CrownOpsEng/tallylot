"""Crypto.com transaction export adapter."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.sources.intake_support import match_intake_by_path_or_header, no_intake_route
from crypto_reconciliation.adapters.sources.mapped_event_support import (
    MappedEventSpec,
    NormalizationIssueSpec,
    mapped_event,
    normalization_issue,
)
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
from crypto_reconciliation.domain.value_objects import parse_decimal
from crypto_reconciliation.ports.adapters import NormalizationResult
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest

HEADER_FIELDS = {
    "Timestamp (UTC)",
    "Transaction Description",
    "Currency",
    "Amount",
    "To Currency",
    "To Amount",
    "Transaction Kind",
}


class CryptoComAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("crypto_com"),
        display_name="Crypto.com",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE, AdapterCapability.INTAKE_ROUTE}),
        description="Normalizes Crypto.com transaction exports.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "crypto.com" in source.lower() or "crypto_com" in source.lower():
            return 100
        if any(HEADER_FIELDS.issubset(set(item.header)) for item in inventory if item.header):
            return 100
        return 0

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("crypto.com", "crypto_com"),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

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

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        events: list[CanonicalEvent] = []
        issues: list[IssueRecord] = []
        for path in sorted(raw_dir.rglob("*.csv")):
            for index, row in enumerate(_read_rows(path), start=2):
                parsed = _normalize_row(profile, path.name, index, row)
                if isinstance(parsed, IssueRecord):
                    issues.append(parsed)
                    continue
                events.append(parsed)
        return NormalizationResult(
            canonical_events=tuple(events),
            canonical_balances=(),
            issues=tuple(issues),
            reviews=(),
            wallet_inventory=(),
        )


def _read_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(csv.DictReader(handle))


def _normalize_row(
    profile: SourceProfile,
    raw_file: str,
    index: int,
    row: dict[str, str],
) -> CanonicalEvent | IssueRecord:
    timestamp = (
        datetime.strptime((row.get("Timestamp (UTC)") or "").strip(), "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=UTC)
        .replace(tzinfo=None)
    )
    row_ref = f"row:{index}"
    description = (row.get("Transaction Description") or "").strip()
    kind = (row.get("Transaction Kind") or "").strip()
    tx_hash = (row.get("Transaction Hash") or "").strip()
    currency = (row.get("Currency") or "").strip().upper()
    amount = parse_decimal((row.get("Amount") or "").strip())
    to_currency = (row.get("To Currency") or "").strip().upper()
    to_amount = parse_decimal((row.get("To Amount") or "").strip())
    if kind == "viban_deposit" and amount is not None and amount > Decimal("0"):
        return mapped_event(
            MappedEventSpec(
                event_id=f"crypto_com:{raw_file}:{row_ref}",
                source=str(profile.source),
                adapter_id="crypto_com",
                account=str(profile.source),
                wallet=str(profile.source),
                timestamp=timestamp,
                event_kind="Deposit",
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_ref,
                render_exchange=str(profile.source),
                asset_in=currency,
                amount_in=amount,
                tx_hash=tx_hash,
                render_tx_id=tx_hash,
                render_tx_id_mode="exact",
                render_notes=kind,
            )
        )
    if kind == "viban_purchase" and amount is not None and amount < Decimal("0") and to_amount is not None:
        return mapped_event(
            MappedEventSpec(
                event_id=f"crypto_com:{raw_file}:{row_ref}",
                source=str(profile.source),
                adapter_id="crypto_com",
                account=str(profile.source),
                wallet=str(profile.source),
                timestamp=timestamp,
                event_kind="Trade",
                description=f"{currency} -> {to_currency}",
                raw_file=raw_file,
                raw_row_ref=row_ref,
                render_exchange=str(profile.source),
                asset_in=to_currency,
                amount_in=to_amount,
                asset_out=currency,
                amount_out=abs(amount),
                tx_hash=tx_hash,
                render_tx_id=tx_hash,
                render_tx_id_mode="exact",
                render_notes=kind,
            )
        )
    if kind == "crypto_withdrawal" and amount is not None and amount < Decimal("0"):
        return mapped_event(
            MappedEventSpec(
                event_id=f"crypto_com:{raw_file}:{row_ref}",
                source=str(profile.source),
                adapter_id="crypto_com",
                account=str(profile.source),
                wallet=str(profile.source),
                timestamp=timestamp,
                event_kind="Withdrawal",
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_ref,
                render_exchange=str(profile.source),
                asset_out=currency,
                amount_out=abs(amount),
                tx_hash=tx_hash,
                render_tx_id=tx_hash,
                render_tx_id_mode="exact",
                render_notes=kind,
            )
        )
    return normalization_issue(
        NormalizationIssueSpec(
            source=str(profile.source),
            adapter_id="crypto_com",
            issue_id=f"crypto_com:{raw_file}:{row_ref}",
            kind="unsupported_row",
            message=f"Unsupported Crypto.com transaction kind: {kind}",
            raw_file=raw_file,
            raw_row_ref=row_ref,
        )
    )


ADAPTER = CryptoComAdapter()
