"""Coinbase retail row normalization."""

from __future__ import annotations

from decimal import Decimal

from crypto_reconciliation.adapters.sources.mapped_transaction_support import MappedTransactionSpec, mapped_transaction
from crypto_reconciliation.domain.models import NormalizedTransaction, SourceProfile
from crypto_reconciliation.domain.value_objects import parse_decimal

from .timestamps import parse_retail_timestamp


def normalize_retail_row(profile: SourceProfile, raw_file: str, row: dict[str, str]) -> NormalizedTransaction:
    row_id = (row.get("ID") or "").strip()
    tx_type = (row.get("Transaction Type") or "").strip().lower()
    asset = (row.get("Asset") or "").strip().upper()
    quantity = parse_decimal((row.get("Quantity Transacted") or "").strip())
    price_currency = (row.get("Price Currency") or "").strip().upper()
    total_amount = money_decimal(row.get("Total (inclusive of fees and/or spread)", ""))
    fee_amount = money_decimal(row.get("Fees and/or Spread", ""))
    description = coinbase_description(tx_type, row.get("Notes", ""), asset, quantity, total_amount)
    timestamp = parse_retail_timestamp((row.get("Timestamp") or "").strip())
    transaction_id = f"coinbase-retail-{row_id}"
    if tx_type == "buy":
        return mapped_transaction(
            MappedTransactionSpec(
                transaction_id=transaction_id,
                source=str(profile.source),
                adapter_id="coinbase",
                account="Coinbase",
                wallet="Coinbase",
                timestamp=timestamp,
                category="trade",
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                asset_in=asset,
                amount_in=quantity,
                asset_out=price_currency,
                amount_out=total_amount,
                fee_asset=price_currency,
                fee_amount=fee_amount,
                tx_hash=transaction_id,
            )
        )
    if tx_type == "sell":
        return mapped_transaction(
            MappedTransactionSpec(
                transaction_id=transaction_id,
                source=str(profile.source),
                adapter_id="coinbase",
                account="Coinbase",
                wallet="Coinbase",
                timestamp=timestamp,
                category="trade",
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                asset_in=price_currency,
                amount_in=total_amount,
                asset_out=asset,
                amount_out=quantity,
                fee_asset=price_currency,
                fee_amount=fee_amount,
                tx_hash=transaction_id,
            )
        )
    if tx_type == "reward income":
        return mapped_transaction(
            MappedTransactionSpec(
                transaction_id=transaction_id,
                source=str(profile.source),
                adapter_id="coinbase",
                account="Coinbase",
                wallet="Coinbase",
                timestamp=timestamp,
                category="interest_income",
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                asset_in=asset,
                amount_in=abs(quantity or Decimal("0")),
                tx_hash=transaction_id,
            )
        )
    if tx_type in {"receive", "deposit"}:
        return mapped_transaction(
            MappedTransactionSpec(
                transaction_id=transaction_id,
                source=str(profile.source),
                adapter_id="coinbase",
                account="Coinbase",
                wallet="Coinbase",
                timestamp=timestamp,
                category="deposit",
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                asset_in=asset,
                amount_in=quantity,
                tx_hash=transaction_id,
            )
        )
    if tx_type in {"send", "withdrawal", "withdraw"}:
        return mapped_transaction(
            MappedTransactionSpec(
                transaction_id=transaction_id,
                source=str(profile.source),
                adapter_id="coinbase",
                account="Coinbase",
                wallet="Coinbase",
                timestamp=timestamp,
                category="withdrawal",
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                asset_out=asset,
                amount_out=abs(quantity or Decimal("0")),
                tx_hash=transaction_id,
            )
        )
    raise ValueError(f"Unsupported Coinbase retail transaction type: {row.get('Transaction Type', '').strip()}")


def coinbase_description(
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


def money_decimal(value: str) -> Decimal | None:
    stripped = value.strip().replace("$", "").replace(",", "")
    return parse_decimal(stripped)
