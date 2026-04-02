"""Coinbase retail row normalization."""

from __future__ import annotations

from decimal import Decimal

from tallylot.adapters.support.drafts import (
    ActivityClassification,
    ActivityDraftSeed,
    EconomicActivityDraft,
    EconomicLegDraft,
    classification,
    economic_leg,
    fee_leg,
)
from tallylot.domain.transactions import EconomicKind, JournalIntent, ProjectionType, TaxTreatmentCode
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.source_profiles import SourceProfile

from .timestamps import parse_retail_timestamp

SUPPORTED_RETAIL_TRANSACTION_TYPES = frozenset(
    {"buy", "sell", "reward income", "receive", "deposit", "send", "withdrawal", "withdraw"}
)


def normalize_retail_row(profile: SourceProfile, raw_file: str, row: dict[str, str]) -> EconomicActivityDraft:
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
    if quantity is None and tx_type not in SUPPORTED_RETAIL_TRANSACTION_TYPES:
        raise ValueError(f"Unsupported Coinbase retail transaction type: {row.get('Transaction Type', '').strip()}")
    if tx_type == "buy" and quantity is not None and total_amount is not None:
        return _draft(
            profile=profile,
            seed=ActivityDraftSeed(
                activity_id=transaction_id,
                timestamp=timestamp,
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                tx_hash=transaction_id,
                provider_operation_key=tx_type,
            ),
            tx_type=tx_type,
            legs=(
                economic_leg(direction="in", asset=asset, amount=quantity),
                economic_leg(direction="out", asset=price_currency, amount=total_amount),
            ),
            fee_legs=_fee_legs(fee_amount, price_currency),
        )
    if tx_type == "sell" and quantity is not None and total_amount is not None:
        return _draft(
            profile=profile,
            seed=ActivityDraftSeed(
                activity_id=transaction_id,
                timestamp=timestamp,
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                tx_hash=transaction_id,
                provider_operation_key=tx_type,
            ),
            tx_type=tx_type,
            legs=(
                economic_leg(direction="in", asset=price_currency, amount=total_amount),
                economic_leg(direction="out", asset=asset, amount=quantity),
            ),
            fee_legs=_fee_legs(fee_amount, price_currency),
        )
    if tx_type == "reward income" and quantity is not None:
        return _draft(
            profile=profile,
            seed=ActivityDraftSeed(
                activity_id=transaction_id,
                timestamp=timestamp,
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                tx_hash=transaction_id,
                provider_operation_key=tx_type,
            ),
            tx_type=tx_type,
            legs=(economic_leg(direction="in", asset=asset, amount=abs(quantity)),),
        )
    if tx_type in {"receive", "deposit"} and quantity is not None:
        return _draft(
            profile=profile,
            seed=ActivityDraftSeed(
                activity_id=transaction_id,
                timestamp=timestamp,
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                tx_hash=transaction_id,
                provider_operation_key=tx_type,
            ),
            tx_type=tx_type,
            legs=(economic_leg(direction="in", asset=asset, amount=quantity),),
        )
    if tx_type in {"send", "withdrawal", "withdraw"} and quantity is not None:
        return _draft(
            profile=profile,
            seed=ActivityDraftSeed(
                activity_id=transaction_id,
                timestamp=timestamp,
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                tx_hash=transaction_id,
                provider_operation_key=tx_type,
            ),
            tx_type=tx_type,
            legs=(economic_leg(direction="out", asset=asset, amount=abs(quantity)),),
        )
    raise ValueError(f"Unsupported Coinbase retail transaction type: {row.get('Transaction Type', '').strip()}")


def _draft(
    *,
    profile: SourceProfile,
    seed: ActivityDraftSeed,
    tx_type: str,
    legs: tuple[EconomicLegDraft, ...],
    fee_legs: tuple[EconomicLegDraft, ...] = (),
) -> EconomicActivityDraft:
    return EconomicActivityDraft(
        activity_id=seed.activity_id,
        source=str(profile.source),
        adapter_id="coinbase",
        account="Coinbase",
        wallet="Coinbase",
        timestamp=seed.timestamp,
        classification=_classification_for_type(tx_type),
        description=seed.description,
        raw_file=seed.raw_file,
        raw_row_ref=seed.raw_row_ref,
        tx_hash=seed.tx_hash,
        provider_operation_key=seed.provider_operation_key,
        operation_group_id=seed.operation_group_id,
        provenance_refs=seed.provenance_refs,
        review_markers=seed.review_markers,
        confidence=seed.confidence,
        status=seed.status,
        legs=legs,
        fee_legs=fee_legs,
    )


def _fee_legs(fee_amount: Decimal | None, fee_asset: str) -> tuple[EconomicLegDraft, ...]:
    if fee_amount is None or fee_amount <= Decimal("0") or not fee_asset:
        return ()
    return (fee_leg(asset=fee_asset, amount=fee_amount),)


def _classification_for_type(tx_type: str) -> ActivityClassification:
    if tx_type in {"buy", "sell"}:
        return classification(
            economic_kind=EconomicKind.SPOT_TRADE,
            projection_type=ProjectionType.TRADE,
            journal_intent=JournalIntent.ASSET_EXCHANGE,
            tax_treatment_code=TaxTreatmentCode.CAPITAL_EXCHANGE,
        )
    if tx_type == "reward income":
        return classification(
            economic_kind=EconomicKind.INTEREST_INCOME,
            projection_type=ProjectionType.INTEREST_INCOME,
            journal_intent=JournalIntent.INCOME_RECOGNITION,
            tax_treatment_code=TaxTreatmentCode.ORDINARY_INCOME,
        )
    if tx_type in {"receive", "deposit"}:
        return classification(
            economic_kind=EconomicKind.ASSET_DEPOSIT,
            projection_type=ProjectionType.DEPOSIT,
            journal_intent=JournalIntent.FUNDING_INFLOW,
            tax_treatment_code=TaxTreatmentCode.NON_TAXABLE_TRANSFER_IN,
        )
    return classification(
        economic_kind=EconomicKind.ASSET_WITHDRAWAL,
        projection_type=ProjectionType.WITHDRAWAL,
        journal_intent=JournalIntent.FUNDING_OUTFLOW,
        tax_treatment_code=TaxTreatmentCode.NON_TAXABLE_TRANSFER_OUT,
    )


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
