"""Binance deposit and withdrawal normalization."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.sources.mapped_event_support import MappedEventSpec, mapped_event
from crypto_reconciliation.domain.models import CanonicalEvent, SourceProfile
from crypto_reconciliation.domain.value_objects import parse_decimal

from .csv_rows import read_rows
from .timestamps import parse_export_timestamp


def normalize_deposit_rows(profile: SourceProfile, path: Path) -> list[CanonicalEvent]:
    events: list[CanonicalEvent] = []
    for index, row in enumerate(read_rows(path), start=2):
        if (row.get("Status") or "").strip().lower() != "completed":
            continue
        amount = parse_decimal((row.get("Amount") or "").strip())
        if amount is None:
            continue
        events.append(
            mapped_event(
                MappedEventSpec(
                    event_id=f"binance:{path.name}:row:{index}",
                    source=str(profile.source),
                    adapter_id="binance",
                    account="Binance",
                    wallet="Funding",
                    timestamp=parse_export_timestamp((row.get("Time") or "").strip(), path.name),
                    event_kind="Deposit",
                    description=f"Binance deposit via {(row.get('Network') or '').strip()}",
                    raw_file=path.name,
                    raw_row_ref=f"row:{index}",
                    asset_in=(row.get("Coin") or "").strip().upper(),
                    amount_in=amount,
                    tx_hash=(row.get("TXID") or "").strip(),
                )
            )
        )
    return events


def normalize_withdraw_rows(profile: SourceProfile, path: Path) -> list[CanonicalEvent]:
    events: list[CanonicalEvent] = []
    for index, row in enumerate(read_rows(path), start=2):
        if (row.get("Status") or "").strip().lower() != "completed":
            continue
        amount = parse_decimal((row.get("Amount") or "").strip())
        fee = parse_decimal((row.get("Fee") or "").strip())
        if amount is None:
            continue
        coin = (row.get("Coin") or "").strip().upper()
        events.append(
            mapped_event(
                MappedEventSpec(
                    event_id=f"binance:{path.name}:row:{index}",
                    source=str(profile.source),
                    adapter_id="binance",
                    account="Binance",
                    wallet="Funding",
                    timestamp=parse_export_timestamp((row.get("Time") or "").strip(), path.name),
                    event_kind="Withdrawal",
                    description=f"Binance withdrawal via {(row.get('Network') or '').strip()}",
                    raw_file=path.name,
                    raw_row_ref=f"row:{index}",
                    asset_out=coin,
                    amount_out=amount,
                    fee_asset=coin if fee is not None and fee > Decimal("0") else "",
                    fee_amount=fee if fee is not None and fee > Decimal("0") else None,
                    tx_hash=(row.get("TXID") or "").strip(),
                )
            )
        )
    return events
