"""Coinbase retail export adapter."""

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

RETAIL_HEADER = (
    "ID",
    "Timestamp",
    "Transaction Type",
    "Asset",
    "Quantity Transacted",
    "Price Currency",
    "Price at Transaction",
    "Subtotal",
    "Total (inclusive of fees and/or spread)",
    "Fees and/or Spread",
    "Notes",
)


class CoinbaseAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("coinbase"),
        display_name="Coinbase",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE}),
        description="Normalizes Coinbase retail all-time exports.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        if "coinbase" in source.lower():
            return 100
        if any(item.relative_path.endswith(".csv") and item.header == RETAIL_HEADER for item in inventory):
            return 100
        if any(_header_for_path(path) == RETAIL_HEADER for path in raw_dir.rglob("*.csv")):
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
        for row in _read_retail_rows(retail_path):
            row_id = (row.get("ID") or "").strip()
            tx_type = (row.get("Transaction Type") or "").strip().lower()
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
                            raw_row_ref=row_id,
                        )
                    )
                )
                continue
            events.append(event)
        return NormalizationResult(
            canonical_events=tuple(events),
            canonical_balances=(),
            issues=tuple(issues),
            reviews=(),
            wallet_inventory=(),
        )


def _retail_path(raw_dir: Path) -> Path | None:
    for path in sorted(raw_dir.rglob("*.csv")):
        if _header_for_path(path) == RETAIL_HEADER:
            return path
    return None


def _header_for_path(path: Path) -> tuple[str, ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        lines = [line.rstrip("\n") for line in handle]
    for index, line in enumerate(lines):
        if line.startswith("ID,Timestamp,Transaction Type,Asset,"):
            return tuple(next(csv.reader([line])))
        if index > 4:
            break
    return ()


def _read_retail_rows(path: Path) -> tuple[dict[str, str], ...]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header_index = next(
        index for index, line in enumerate(lines) if line.startswith("ID,Timestamp,Transaction Type,Asset,")
    )
    reader = csv.DictReader(lines[header_index:])
    return tuple(reader)


def _normalize_row(profile: SourceProfile, raw_file: str, row: dict[str, str]) -> CanonicalEvent:
    row_id = (row.get("ID") or "").strip()
    tx_type = (row.get("Transaction Type") or "").strip().lower()
    asset = (row.get("Asset") or "").strip().upper()
    quantity = parse_decimal((row.get("Quantity Transacted") or "").strip())
    price_currency = (row.get("Price Currency") or "").strip().upper()
    total_amount = _money_decimal(row.get("Total (inclusive of fees and/or spread)", ""))
    fee_amount = _money_decimal(row.get("Fees and/or Spread", ""))
    description = _coinbase_description(tx_type, row.get("Notes", ""), asset, quantity, total_amount)
    timestamp = (
        datetime.strptime((row.get("Timestamp") or "").strip(), "%Y-%m-%d %H:%M:%S UTC")
        .replace(tzinfo=UTC)
        .replace(tzinfo=None)
    )
    event_id = f"coinbase-retail-{row_id}"
    if tx_type == "buy":
        return mapped_event(
            MappedEventSpec(
                event_id=event_id,
                source=str(profile.source),
                adapter_id="coinbase",
                account="Coinbase",
                wallet="Coinbase",
                timestamp=timestamp,
                event_kind="Trade",
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                render_exchange="Coinbase",
                asset_in=asset,
                amount_in=quantity,
                asset_out=price_currency,
                amount_out=total_amount,
                fee_asset=price_currency,
                fee_amount=fee_amount,
                tx_hash=event_id,
                render_tx_id=event_id,
                render_tx_id_mode="ignore",
                render_match_window_seconds="20",
                render_fee_tolerance="0.03000000",
                render_notes="Retail Buy row normalized from Coinbase raw export",
            )
        )
    if tx_type == "sell":
        return mapped_event(
            MappedEventSpec(
                event_id=event_id,
                source=str(profile.source),
                adapter_id="coinbase",
                account="Coinbase",
                wallet="Coinbase",
                timestamp=timestamp,
                event_kind="Trade",
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                render_exchange="Coinbase",
                asset_in=price_currency,
                amount_in=total_amount,
                asset_out=asset,
                amount_out=quantity,
                fee_asset=price_currency,
                fee_amount=fee_amount,
                tx_hash=event_id,
                render_tx_id=event_id,
                render_tx_id_mode="ignore",
                render_match_window_seconds="20",
                render_fee_tolerance="0.03000000",
                render_notes="Retail Sell row normalized from Coinbase raw export",
            )
        )
    if tx_type in {"receive", "deposit"}:
        return mapped_event(
            MappedEventSpec(
                event_id=event_id,
                source=str(profile.source),
                adapter_id="coinbase",
                account="Coinbase",
                wallet="Coinbase",
                timestamp=timestamp,
                event_kind="Deposit",
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                render_exchange="Coinbase",
                asset_in=asset,
                amount_in=quantity,
                tx_hash=event_id,
                render_tx_id=event_id,
                render_tx_id_mode="ignore",
                render_match_window_seconds="20",
                render_fee_tolerance="0.03000000",
                render_notes="Retail receive row normalized from Coinbase raw export",
            )
        )
    if tx_type in {"send", "withdrawal", "withdraw"}:
        return mapped_event(
            MappedEventSpec(
                event_id=event_id,
                source=str(profile.source),
                adapter_id="coinbase",
                account="Coinbase",
                wallet="Coinbase",
                timestamp=timestamp,
                event_kind="Withdrawal",
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                render_exchange="Coinbase",
                asset_out=asset,
                amount_out=quantity,
                tx_hash=event_id,
                render_tx_id=event_id,
                render_tx_id_mode="ignore",
                render_match_window_seconds="20",
                render_fee_tolerance="0.03000000",
                render_notes="Retail send row normalized from Coinbase raw export",
            )
        )
    raise ValueError(f"Unsupported Coinbase retail transaction type: {row.get('Transaction Type', '').strip()}")


def _coinbase_description(
    tx_type: str,
    notes: str,
    asset: str,
    quantity: Decimal | None,
    quote_amount: Decimal | None,
) -> str:
    note = notes.strip()
    if note:
        return note.replace("  ", " ").replace(" for ", " for $", 1) if tx_type == "buy" and "$" not in note else note
    if tx_type == "buy" and quantity is not None and quote_amount is not None:
        return f"Bought {quantity} {asset} for {quote_amount}"
    return f"Coinbase {tx_type or 'transaction'}"


def _money_decimal(value: str) -> Decimal | None:
    stripped = value.strip().replace("$", "").replace(",", "")
    return parse_decimal(stripped)


ADAPTER = CoinbaseAdapter()
