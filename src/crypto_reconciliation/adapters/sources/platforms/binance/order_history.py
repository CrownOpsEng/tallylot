"""Binance convert and C2C order normalization."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from crypto_reconciliation.adapters.sources.mapped_transaction_support import MappedTransactionSpec, mapped_transaction
from crypto_reconciliation.domain.models import NormalizedTransaction, SourceProfile
from crypto_reconciliation.domain.value_objects import parse_decimal

from .csv_rows import read_rows
from .field_parsing import amount_with_asset
from .timestamps import parse_export_timestamp, parse_transaction_history_timestamp


def normalize_convert_order_rows(
    profile: SourceProfile,
    path: Path,
) -> tuple[list[NormalizedTransaction], set[datetime]]:
    events: list[NormalizedTransaction] = []
    matched_times: set[datetime] = set()
    for index, row in enumerate(read_rows(path), start=2):
        if (row.get("Status") or "").strip().lower() != "successful":
            continue
        buy_amount, buy_asset = amount_with_asset(row.get("Buy", ""))
        sell_amount, sell_asset = amount_with_asset(row.get("Sell", ""))
        if buy_amount is None or sell_amount is None or not buy_asset or not sell_asset:
            continue
        date_updated = (row.get("Date Updated") or row.get("Time") or "").strip()
        matched_times.add(parse_transaction_history_timestamp(date_updated))
        events.append(
            mapped_transaction(
                MappedTransactionSpec(
                    transaction_id=f"binance:{path.name}:convert:{index}",
                    source=str(profile.source),
                    adapter_id="binance",
                    account=(row.get("Wallet") or "").strip() or "Spot",
                    wallet=(row.get("Wallet") or "").strip() or "Spot",
                    timestamp=parse_export_timestamp(date_updated, path.name),
                    category="trade",
                    description=f"Binance convert {(row.get('Pair') or '').strip()}",
                    raw_file=path.name,
                    raw_row_ref=f"row:{index}",
                    asset_in=buy_asset,
                    amount_in=buy_amount,
                    asset_out=sell_asset,
                    amount_out=sell_amount,
                )
            )
        )
    return events, matched_times


def normalize_c2c_order_rows(
    profile: SourceProfile,
    path: Path,
) -> tuple[list[NormalizedTransaction], set[datetime]]:
    events: list[NormalizedTransaction] = []
    matched_times: set[datetime] = set()
    for index, row in enumerate(read_rows(path), start=2):
        if (row.get("Status") or "").strip().lower() != "completed":
            continue
        quantity = parse_decimal((row.get("Quantity") or "").strip())
        total_price = parse_decimal((row.get("Total Price") or "").strip())
        asset = (row.get("Asset") or "").strip().upper()
        fiat = (row.get("Fiat Type") or "").strip().upper()
        if quantity is None or total_price is None or not asset or not fiat:
            continue
        order_type = (row.get("Order Type") or "").strip().upper()
        created_time = (row.get("Created Time") or "").strip()
        matched_times.add(parse_transaction_history_timestamp(created_time))
        if order_type == "SELL":
            asset_in = fiat
            amount_in = total_price
            asset_out = asset
            amount_out = quantity
        else:
            asset_in = asset
            amount_in = quantity
            asset_out = fiat
            amount_out = total_price
        events.append(
            mapped_transaction(
                MappedTransactionSpec(
                    transaction_id=f"binance:{path.name}:c2c:{(row.get('Order Number') or '').strip() or index}",
                    source=str(profile.source),
                    adapter_id="binance",
                    account="Funding",
                    wallet="Funding",
                    timestamp=parse_export_timestamp(created_time, path.name),
                    category="trade",
                    description=f"Binance C2C {(row.get('Order Type') or '').strip()} {asset}/{fiat}",
                    raw_file=path.name,
                    raw_row_ref=f"row:{index}",
                    asset_in=asset_in,
                    amount_in=amount_in,
                    asset_out=asset_out,
                    amount_out=amount_out,
                )
            )
        )
    return events, matched_times
