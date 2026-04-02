"""Wealthsimple crypto export adapter."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

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

BROKER_HEADER = (
    "transaction_date",
    "settlement_date",
    "account_id",
    "account_type",
    "activity_type",
    "activity_sub_type",
    "direction",
    "symbol",
    "name",
    "currency",
    "quantity",
    "unit_price",
    "commission",
    "net_cash_amount",
)
ACTIVITY_HEADER = (
    "transaction_date",
    "settlement_date",
    "account_id",
    "account_type",
    "activity_type",
    "activity_sub_type",
    "quantity",
    "currency",
    "symbol",
    "commission",
    "net_cash_amount",
)


class WealthsimpleAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("wealthsimple"),
        display_name="Wealthsimple",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE}),
        description="Normalizes Wealthsimple crypto activity exports.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "wealthsimple" in source.lower():
            return 100
        if any(item.header in {BROKER_HEADER, ACTIVITY_HEADER} for item in inventory):
            return 100
        return 0

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        rows_with_dates = sum(1 for item in profile.file_inventory if item.date_field)
        return {
            "status": "passed",
            "issue_count": 0,
            "rows_with_dates": rows_with_dates,
            "mode_counts": {"date_only": rows_with_dates} if rows_with_dates else {},
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
        for path in sorted(raw_dir.glob("*.csv")):
            for index, row in enumerate(_read_rows(path), start=2):
                if (row.get("account_type") or "").strip().lower() != "crypto":
                    continue
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
    activity_type = (row.get("activity_type") or "").strip()
    activity_sub_type = (row.get("activity_sub_type") or "").strip()
    row_ref = f"row:{index}"
    timestamp = _parse_date((row.get("settlement_date") or row.get("transaction_date") or "").strip())
    account_id = (row.get("account_id") or "").strip()
    symbol = (row.get("symbol") or "").strip().upper()
    currency = (row.get("currency") or "").strip().upper()
    quantity = parse_decimal((row.get("quantity") or "").strip())
    commission = parse_decimal((row.get("commission") or "").strip())
    net_cash_amount = parse_decimal((row.get("net_cash_amount") or "").strip())
    if activity_type.lower() == "trade" and activity_sub_type.upper() == "BUY":
        return mapped_event(
            MappedEventSpec(
                event_id=f"wealthsimple:{raw_file}:{row_ref}",
                source=str(profile.source),
                adapter_id="wealthsimple",
                account=account_id,
                wallet=account_id,
                timestamp=timestamp,
                event_kind="Trade",
                description="Wealthsimple Crypto buy",
                raw_file=raw_file,
                raw_row_ref=row_ref,
                render_exchange=str(profile.source),
                asset_in=symbol,
                amount_in=quantity,
                asset_out=currency,
                amount_out=abs(net_cash_amount) if net_cash_amount is not None else None,
                fee_asset=currency if commission is not None and commission > Decimal("0") else "",
                fee_amount=commission if commission is not None and commission > Decimal("0") else None,
                render_tx_id_mode="ignore",
                render_match_window_seconds="86399",
                render_notes="Trade:BUY",
            )
        )
    if activity_type.lower() == "trade" and activity_sub_type.upper() == "SELL":
        return mapped_event(
            MappedEventSpec(
                event_id=f"wealthsimple:{raw_file}:{row_ref}",
                source=str(profile.source),
                adapter_id="wealthsimple",
                account=account_id,
                wallet=account_id,
                timestamp=timestamp,
                event_kind="Trade",
                description="Wealthsimple Crypto sell",
                raw_file=raw_file,
                raw_row_ref=row_ref,
                render_exchange=str(profile.source),
                asset_in=currency,
                amount_in=abs(net_cash_amount) if net_cash_amount is not None else None,
                asset_out=symbol,
                amount_out=quantity,
                fee_asset=currency if commission is not None and commission > Decimal("0") else "",
                fee_amount=commission if commission is not None and commission > Decimal("0") else None,
                render_tx_id_mode="ignore",
                render_match_window_seconds="86399",
                render_notes="Trade:SELL",
            )
        )
    return normalization_issue(
        NormalizationIssueSpec(
            source=str(profile.source),
            adapter_id="wealthsimple",
            issue_id=f"wealthsimple:{raw_file}:{row_ref}",
            kind="unsupported_row",
            message=f"Unsupported Wealthsimple crypto activity: {activity_type}/{activity_sub_type}",
            raw_file=raw_file,
            raw_row_ref=row_ref,
        )
    )


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC).replace(tzinfo=None)


ADAPTER = WealthsimpleAdapter()
