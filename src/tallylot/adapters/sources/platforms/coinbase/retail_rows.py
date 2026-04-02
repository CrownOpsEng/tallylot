"""Coinbase retail row normalization."""

from __future__ import annotations

from decimal import Decimal

from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    ActivityClassification,
    ActivityDraftSeed,
    EconomicActivityDraft,
    EconomicLegDraft,
    LegKind,
    classification,
    economic_leg,
)
from tallylot.domain.transactions import EconomicKind, FactDirection, JournalIntent, ProjectionType, TaxTreatmentCode
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
    subtotal_amount = money_decimal(row.get("Subtotal", ""))
    total_amount = money_decimal(row.get("Total (inclusive of fees and/or spread)", ""))
    fee_amount = money_decimal(row.get("Fees and/or Spread", ""))
    description = coinbase_description(tx_type, row.get("Notes", ""), asset, quantity, total_amount)
    timestamp = parse_retail_timestamp((row.get("Timestamp") or "").strip())
    transaction_id = f"coinbase-retail-{row_id}"
    if quantity is None and tx_type not in SUPPORTED_RETAIL_TRANSACTION_TYPES:
        raise ValueError(f"Unsupported Coinbase retail transaction type: {row.get('Transaction Type', '').strip()}")
    if (
        tx_type == "buy"
        and quantity is not None
        and (cash_amount := _retail_cash_amount(tx_type, subtotal_amount, total_amount, fee_amount)) is not None
    ):
        return _draft(
            profile=profile,
            seed=ActivityDraftSeed(
                activity_id=transaction_id,
                timestamp=timestamp,
                leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                tx_hash=transaction_id,
                provider_operation_key=tx_type,
            ),
            tx_type=tx_type,
            legs=(
                economic_leg(direction="in", kind=LegKind.PRIMARY, asset=asset, amount=quantity),
                economic_leg(direction="out", kind=LegKind.PRIMARY, asset=price_currency, amount=cash_amount),
                *_charge_legs(fee_amount, price_currency, attributed_to_direction="out"),
            ),
        )
    if (
        tx_type == "sell"
        and quantity is not None
        and (cash_amount := _retail_cash_amount(tx_type, subtotal_amount, total_amount, fee_amount)) is not None
    ):
        return _draft(
            profile=profile,
            seed=ActivityDraftSeed(
                activity_id=transaction_id,
                timestamp=timestamp,
                leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                tx_hash=transaction_id,
                provider_operation_key=tx_type,
            ),
            tx_type=tx_type,
            legs=(
                economic_leg(direction="in", kind=LegKind.PRIMARY, asset=price_currency, amount=cash_amount),
                economic_leg(direction="out", kind=LegKind.PRIMARY, asset=asset, amount=quantity),
                *_charge_legs(fee_amount, price_currency, attributed_to_direction="in"),
            ),
        )
    if tx_type == "reward income" and quantity is not None:
        return _draft(
            profile=profile,
            seed=ActivityDraftSeed(
                activity_id=transaction_id,
                timestamp=timestamp,
                leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                tx_hash=transaction_id,
                provider_operation_key=tx_type,
            ),
            tx_type=tx_type,
            legs=(economic_leg(direction="in", kind=LegKind.PRIMARY, asset=asset, amount=abs(quantity)),),
        )
    if tx_type in {"receive", "deposit"} and quantity is not None:
        return _draft(
            profile=profile,
            seed=ActivityDraftSeed(
                activity_id=transaction_id,
                timestamp=timestamp,
                leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                tx_hash=transaction_id,
                provider_operation_key=tx_type,
            ),
            tx_type=tx_type,
            legs=(economic_leg(direction="in", kind=LegKind.PRIMARY, asset=asset, amount=quantity),),
        )
    if tx_type in {"send", "withdrawal", "withdraw"} and quantity is not None:
        return _draft(
            profile=profile,
            seed=ActivityDraftSeed(
                activity_id=transaction_id,
                timestamp=timestamp,
                leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_id,
                tx_hash=transaction_id,
                provider_operation_key=tx_type,
            ),
            tx_type=tx_type,
            legs=(economic_leg(direction="out", kind=LegKind.PRIMARY, asset=asset, amount=abs(quantity)),),
        )
    raise ValueError(f"Unsupported Coinbase retail transaction type: {row.get('Transaction Type', '').strip()}")


def _draft(
    *,
    profile: SourceProfile,
    seed: ActivityDraftSeed,
    tx_type: str,
    legs: tuple[EconomicLegDraft, ...],
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
        leg_policy=seed.leg_policy,
        legs=legs,
    )


def _charge_legs(
    fee_amount: Decimal | None,
    fee_asset: str,
    *,
    attributed_to_direction: FactDirection,
) -> tuple[EconomicLegDraft, ...]:
    if fee_amount is None or fee_amount <= Decimal("0") or not fee_asset:
        return ()
    return (
        economic_leg(
            direction="out",
            kind=LegKind.CHARGE,
            asset=fee_asset,
            amount=fee_amount,
            subtype="trading_fee",
            attributed_to_direction=attributed_to_direction,
        ),
    )


def _retail_cash_amount(
    tx_type: str,
    subtotal_amount: Decimal | None,
    total_amount: Decimal | None,
    fee_amount: Decimal | None,
) -> Decimal | None:
    if subtotal_amount is not None:
        return subtotal_amount
    if total_amount is None:
        return None
    if fee_amount is None or fee_amount <= Decimal("0"):
        return total_amount
    cash_amount = total_amount - fee_amount if tx_type == "buy" else total_amount + fee_amount
    return cash_amount if cash_amount > Decimal("0") else None


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
