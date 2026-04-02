"""Binance convert and C2C order normalization."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from crypto_reconciliation.adapters.support.drafts import (
    EconomicActivityDraft,
    classification,
    economic_leg,
)
from crypto_reconciliation.domain.models import SourceProfile
from crypto_reconciliation.domain.value_objects import parse_decimal

from .csv_rows import read_rows
from .field_parsing import amount_with_asset
from .timestamps import parse_export_timestamp, parse_transaction_history_timestamp

SUPPORTED_ORDER_EXPORTS = frozenset({"convert", "c2c"})


def normalize_convert_order_rows(
    profile: SourceProfile,
    path: Path,
) -> tuple[list[EconomicActivityDraft], set[datetime]]:
    drafts: list[EconomicActivityDraft] = []
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
        drafts.append(
            EconomicActivityDraft(
                activity_id=f"binance:{path.name}:convert:{index}",
                source=str(profile.source),
                adapter_id="binance",
                account=(row.get("Wallet") or "").strip() or "Spot",
                wallet=(row.get("Wallet") or "").strip() or "Spot",
                timestamp=parse_export_timestamp(date_updated, path.name),
                classification=classification(
                    economic_kind="asset_conversion",
                    projection_type="Trade",
                    journal_intent="asset_exchange",
                    tax_treatment_code="capital_exchange",
                ),
                description=f"Binance convert {(row.get('Pair') or '').strip()}",
                raw_file=path.name,
                raw_row_ref=f"row:{index}",
                provider_operation_key="order_history:convert",
                legs=(
                    economic_leg(direction="in", asset=buy_asset, amount=buy_amount),
                    economic_leg(direction="out", asset=sell_asset, amount=sell_amount),
                ),
            )
        )
    return drafts, matched_times


def normalize_c2c_order_rows(
    profile: SourceProfile,
    path: Path,
) -> tuple[list[EconomicActivityDraft], set[datetime]]:
    drafts: list[EconomicActivityDraft] = []
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
            legs = (
                economic_leg(direction="in", asset=fiat, amount=total_price),
                economic_leg(direction="out", asset=asset, amount=quantity),
            )
        else:
            legs = (
                economic_leg(direction="in", asset=asset, amount=quantity),
                economic_leg(direction="out", asset=fiat, amount=total_price),
            )
        drafts.append(
            EconomicActivityDraft(
                activity_id=f"binance:{path.name}:c2c:{(row.get('Order Number') or '').strip() or index}",
                source=str(profile.source),
                adapter_id="binance",
                account="Funding",
                wallet="Funding",
                timestamp=parse_export_timestamp(created_time, path.name),
                classification=classification(
                    economic_kind="p2p_trade",
                    projection_type="Trade",
                    journal_intent="asset_exchange",
                    tax_treatment_code="capital_exchange",
                ),
                description=f"Binance C2C {(row.get('Order Type') or '').strip()} {asset}/{fiat}",
                raw_file=path.name,
                raw_row_ref=f"row:{index}",
                provider_operation_key=f"order_history:c2c:{order_type.lower()}",
                legs=legs,
            )
        )
    return drafts, matched_times
