"""Structured CSV source adapter."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    CanonicalBalance,
    CanonicalEvent,
    FileInventoryEntry,
    IssueRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, EventId, SourceId
from crypto_reconciliation.domain.value_objects import parse_decimal
from crypto_reconciliation.ports.adapters import NormalizationResult

REQUIRED_HEADER = (
    "timestamp",
    "event_kind",
    "asset_in",
    "amount_in",
    "asset_out",
    "amount_out",
    "fee_asset",
    "fee_amount",
    "tx_hash",
    "description",
    "account",
    "wallet",
)


class StructuredCsvSourceAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("structured_csv"),
        display_name="Structured CSV",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE, AdapterCapability.WALLET_INVENTORY}),
        description="Normalizes a strongly typed structured CSV source capture.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del source, raw_dir
        for item in inventory:
            if item.relative_path == "transactions.csv" and item.header == REQUIRED_HEADER:
                return 100
        return 0

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        path = raw_dir / "transactions.csv"
        events: list[CanonicalEvent] = []
        balances: dict[tuple[str, str, str], Decimal] = {}
        wallet_rows: dict[str, WalletInventoryRecord] = {}
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for index, row in enumerate(reader, start=2):
                timestamp = datetime.strptime(
                    row["timestamp"],
                    "%Y-%m-%d %H:%M:%S",
                ).replace(tzinfo=UTC)
                amount_in = parse_decimal(row["amount_in"])
                amount_out = parse_decimal(row["amount_out"])
                fee_amount = parse_decimal(row["fee_amount"])
                account = row["account"]
                wallet = row["wallet"]
                events.append(
                    CanonicalEvent(
                        event_id=EventId(f"{profile.source}:{index}"),
                        source=SourceId(str(profile.source)),
                        adapter_id=AdapterId(str(self.manifest.adapter_id)),
                        account=account,
                        wallet=wallet,
                        timestamp=timestamp,
                        event_kind=row["event_kind"],
                        description=row["description"],
                        asset_in=AssetSymbol(row["asset_in"]) if row["asset_in"] else None,
                        amount_in=amount_in,
                        asset_out=AssetSymbol(row["asset_out"]) if row["asset_out"] else None,
                        amount_out=amount_out,
                        fee_asset=AssetSymbol(row["fee_asset"]) if row["fee_asset"] else None,
                        fee_amount=fee_amount,
                        tx_hash=row["tx_hash"] or None,
                        raw_file="transactions.csv",
                        raw_row_ref=str(index),
                        render_type=row["event_kind"],
                        render_exchange=account,
                        render_comment=row["description"],
                    )
                )
                if row["asset_in"] and amount_in is not None:
                    key = (account, wallet, row["asset_in"])
                    balances[key] = balances.get(key, Decimal("0")) + amount_in
                if row["asset_out"] and amount_out is not None:
                    key = (account, wallet, row["asset_out"])
                    balances[key] = balances.get(key, Decimal("0")) - amount_out
                if row["fee_asset"] and fee_amount is not None:
                    key = (account, wallet, row["fee_asset"])
                    balances[key] = balances.get(key, Decimal("0")) - fee_amount
                wallet_id = f"{profile.source}:{account}:{wallet}"
                wallet_rows[wallet_id] = WalletInventoryRecord(
                    wallet_id=wallet_id,
                    source=str(profile.source),
                    account=account,
                    wallet=wallet,
                    evidence_path=str(path),
                    identifier_kind="account_wallet",
                    identifier_value=f"{account}:{wallet}",
                )

        as_of = max(event.timestamp for event in events) if events else datetime.now(UTC)
        balance_rows = tuple(
            CanonicalBalance(
                source=SourceId(str(profile.source)),
                account=account,
                wallet=wallet,
                asset=AssetSymbol(asset),
                quantity=quantity,
                as_of=as_of,
            )
            for (account, wallet, asset), quantity in sorted(balances.items())
        )
        return NormalizationResult(
            canonical_events=tuple(events),
            canonical_balances=balance_rows,
            issues=tuple(
                [] if events else [
                    IssueRecord(
                        issue_id=f"{profile.source}:empty",
                        source=str(profile.source),
                        adapter_id=str(self.manifest.adapter_id),
                        severity="high",
                        kind="empty_source",
                        message="No rows were available for normalization.",
                    )
                ]
            ),
            wallet_inventory=tuple(wallet_rows.values()),
        )


ADAPTER = StructuredCsvSourceAdapter()
