"""Shakepay export adapter."""

from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

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

TORONTO = ZoneInfo("America/Toronto")


class ShakepayAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("shakepay"),
        display_name="Shakepay",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE}),
        description="Normalizes Shakepay cash and crypto export summaries.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "shakepay" in source.lower():
            return 100
        if any("crypto_transactions_summary.csv" in item.relative_path for item in inventory):
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
            "mode_counts": {"america_toronto": rows_with_dates} if rows_with_dates else {},
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
                parsed = _normalize_row(profile, path.name, index, row)
                if isinstance(parsed, IssueRecord):
                    issues.append(parsed)
                    continue
                if parsed is not None:
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
) -> CanonicalEvent | IssueRecord | None:
    row_ref = f"row:{index}"
    timestamp = _parse_local_timestamp((row.get("Date") or "").strip())
    if raw_file == "cash_transactions_summary.csv":
        debit = parse_decimal((row.get("Debit") or "").strip())
        credit = parse_decimal((row.get("Credit") or "").strip())
        description = (row.get("Description") or "").strip()
        row_type = (row.get("Type") or "").strip()
        event_kind = ""
        asset_in = ""
        amount_in = None
        asset_out = ""
        amount_out = None
        if credit is not None and credit > Decimal("0"):
            event_kind = "Deposit"
            asset_in = "CAD"
            amount_in = credit
        elif debit is not None and debit > Decimal("0"):
            event_kind = "Expense (non taxable)" if row_type == "Card purchase" else "Withdrawal"
            asset_out = "CAD"
            amount_out = debit
        else:
            return None
        return mapped_event(
            MappedEventSpec(
                event_id=f"shakepay:{raw_file}:{row_ref}",
                source=str(profile.source),
                adapter_id="shakepay",
                account="Shakepay",
                wallet="Shakepay",
                timestamp=timestamp,
                event_kind=event_kind,
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_ref,
                render_exchange=str(profile.source),
                asset_in=asset_in,
                amount_in=amount_in,
                asset_out=asset_out,
                amount_out=amount_out,
                tx_hash=f"shakepay:{raw_file}:{row_ref}",
                render_tx_id=f"shakepay:{raw_file}:{row_ref}",
                render_tx_id_mode="exact",
                render_notes=row_type,
            )
        )
    debited_amount = parse_decimal((row.get("Amount Debited") or "").strip())
    credited_amount = parse_decimal((row.get("Amount Credited") or "").strip())
    debited_asset = (row.get("Asset Debited") or "").strip().upper()
    credited_asset = (row.get("Asset Credited") or "").strip().upper()
    description = (row.get("Description") or "").strip().lower()
    row_type = (row.get("Type") or "").strip()
    event_id = f"shakepay:{raw_file}:{row_ref}"
    if row_type == "Reward" and credited_amount is not None and credited_asset:
        spec = MappedEventSpec(
            event_id=event_id,
            source=str(profile.source),
            adapter_id="shakepay",
            account="Shakepay",
            wallet="Shakepay",
            timestamp=timestamp,
            event_kind="Reward / Bonus",
            description=description,
            raw_file=raw_file,
            raw_row_ref=row_ref,
            render_exchange=str(profile.source),
            asset_in=credited_asset,
            amount_in=credited_amount,
            tx_hash=event_id,
            render_tx_id=event_id,
            render_tx_id_mode="exact",
            render_notes=row_type,
        )
        return mapped_event(spec)
    if row_type == "Buy" and debited_amount is not None and credited_amount is not None:
        spec = MappedEventSpec(
            event_id=event_id,
            source=str(profile.source),
            adapter_id="shakepay",
            account="Shakepay",
            wallet="Shakepay",
            timestamp=timestamp,
            event_kind="Trade",
            description=(row.get("Description") or "").strip(),
            raw_file=raw_file,
            raw_row_ref=row_ref,
            render_exchange=str(profile.source),
            asset_in=credited_asset,
            amount_in=credited_amount,
            asset_out=debited_asset,
            amount_out=debited_amount,
            tx_hash=event_id,
            render_tx_id=event_id,
            render_tx_id_mode="exact",
            render_notes=row_type,
        )
        return mapped_event(spec)
    if row_type == "Send" and debited_amount is not None and debited_asset:
        spec = MappedEventSpec(
            event_id=event_id,
            source=str(profile.source),
            adapter_id="shakepay",
            account="Shakepay",
            wallet="Shakepay",
            timestamp=timestamp,
            event_kind="Withdrawal",
            description=(row.get("Description") or "").strip(),
            raw_file=raw_file,
            raw_row_ref=row_ref,
            render_exchange=str(profile.source),
            asset_out=debited_asset,
            amount_out=debited_amount,
            tx_hash=event_id,
            render_tx_id=event_id,
            render_tx_id_mode="exact",
            render_notes=row_type,
        )
        return mapped_event(spec)
    return normalization_issue(
        NormalizationIssueSpec(
            source=str(profile.source),
            adapter_id="shakepay",
            issue_id=event_id,
            kind="unsupported_row",
            message=f"Unsupported Shakepay row type: {row_type}",
            raw_file=raw_file,
            raw_row_ref=row_ref,
        )
    )


def _parse_local_timestamp(value: str) -> datetime:
    local = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TORONTO)
    return local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


ADAPTER = ShakepayAdapter()
