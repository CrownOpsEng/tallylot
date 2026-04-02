"""Structured CSV translation helpers."""

from __future__ import annotations

from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    ActivityClassification,
    EconomicActivityDraft,
    EconomicLegDraft,
    FactLegPolicy,
    LegKind,
    LegShapeLimit,
    classification,
    economic_leg,
)
from tallylot.domain.issues import NormalizationReviewRecord
from tallylot.domain.transactions import EconomicKind, FactDirection, JournalIntent, ProjectionType, TaxTreatmentCode
from tallylot.domain.value_objects import parse_decimal, parse_timestamp
from tallylot.ports.source_profiles import SourceProfile

from .contracts import TRANSACTIONS_FILENAME
from .validation import StructuredCsvRowValidator

type StructuredCategory = str


def translate_row(
    profile: SourceProfile,
    row: dict[str, str],
    index: int,
    *,
    validator: StructuredCsvRowValidator,
) -> tuple[EconomicActivityDraft, tuple[NormalizationReviewRecord, ...]]:
    amount_out, amount_out_review = validator.normalize_outbound_amount(index, "amount_out", row["amount_out"])
    charge_amount, charge_amount_review = validator.normalize_outbound_amount(
        index,
        "charge_amount",
        row["charge_amount"],
    )
    reviews = tuple(review for review in (amount_out_review, charge_amount_review) if review is not None)
    account = row["account"].strip()
    wallet = row["wallet"].strip()
    legs: list[EconomicLegDraft] = []
    if row["asset_in"] and (amount_in := parse_decimal(row["amount_in"])) is not None:
        legs.append(economic_leg(direction="in", kind=LegKind.PRIMARY, asset=row["asset_in"], amount=amount_in))
    if row["asset_out"] and amount_out is not None:
        legs.append(economic_leg(direction="out", kind=LegKind.PRIMARY, asset=row["asset_out"], amount=amount_out))
    if row["charge_asset"] and charge_amount is not None:
        legs.append(
            economic_leg(
                direction="out",
                kind=LegKind.CHARGE,
                asset=row["charge_asset"],
                amount=charge_amount,
                attributed_to_direction=_side_value(row["charge_side"]),
            )
        )
    if row["rebate_asset"] and (rebate_amount := parse_decimal(row["rebate_amount"])) is not None:
        legs.append(
            economic_leg(
                direction="in",
                kind=LegKind.REBATE,
                asset=row["rebate_asset"],
                amount=rebate_amount,
                attributed_to_direction=_side_value(row["rebate_side"]),
            )
        )
    category = row["category"]
    return EconomicActivityDraft(
        activity_id=f"{profile.source}:{index}",
        source=str(profile.source),
        adapter_id=validator.feedback.adapter_id,
        account=account,
        wallet=wallet,
        timestamp=parse_timestamp(row["timestamp"]),
        classification=classification_for_category(category),
        description=row["description"],
        raw_file=TRANSACTIONS_FILENAME,
        raw_row_ref=str(index),
        tx_hash=row["tx_hash"] or "",
        provider_operation_key=f"structured_csv:{category}",
        legs=tuple(legs),
        leg_policy=policy_for_row(row),
    ), reviews


def policy_for_row(row: dict[str, str]) -> FactLegPolicy:
    has_charge = bool(row["charge_asset"].strip() and row["charge_amount"].strip())
    has_rebate = bool(row["rebate_asset"].strip() and row["rebate_amount"].strip())
    has_in = bool(row["asset_in"].strip())
    has_out = bool(row["asset_out"].strip())
    if has_in and has_out and has_charge and not has_rebate:
        return TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY
    if has_in and has_out and not has_charge and not has_rebate:
        return TWO_SIDED_PRIMARY_EXCHANGE_POLICY
    if (has_in ^ has_out) and not has_charge and not has_rebate:
        return SINGLE_PRIMARY_ACTIVITY_POLICY

    limits = [LegShapeLimit(kind=LegKind.PRIMARY, max_count=2, max_in_count=1, max_out_count=1)]
    if has_charge:
        limits.append(LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_in_count=0, max_out_count=1))
    if has_rebate:
        limits.append(LegShapeLimit(kind=LegKind.REBATE, max_count=1, max_in_count=1, max_out_count=0))
    return FactLegPolicy(limits=tuple(limits))


def _side_value(raw_value: str) -> FactDirection | None:
    stripped = raw_value.strip()
    if stripped == "in":
        return "in"
    if stripped == "out":
        return "out"
    return None


def classification_for_category(category: StructuredCategory) -> ActivityClassification:
    mapping: dict[str, tuple[EconomicKind, ProjectionType, JournalIntent, TaxTreatmentCode]] = {
        "trade": (
            EconomicKind.SPOT_TRADE,
            ProjectionType.TRADE,
            JournalIntent.ASSET_EXCHANGE,
            TaxTreatmentCode.CAPITAL_EXCHANGE,
        ),
        "deposit": (
            EconomicKind.ASSET_DEPOSIT,
            ProjectionType.DEPOSIT,
            JournalIntent.FUNDING_INFLOW,
            TaxTreatmentCode.NON_TAXABLE_TRANSFER_IN,
        ),
        "withdrawal": (
            EconomicKind.ASSET_WITHDRAWAL,
            ProjectionType.WITHDRAWAL,
            JournalIntent.FUNDING_OUTFLOW,
            TaxTreatmentCode.NON_TAXABLE_TRANSFER_OUT,
        ),
        "interest_income": (
            EconomicKind.INTEREST_INCOME,
            ProjectionType.INTEREST_INCOME,
            JournalIntent.INCOME_RECOGNITION,
            TaxTreatmentCode.ORDINARY_INCOME,
        ),
        "reward": (
            EconomicKind.PLATFORM_REWARD,
            ProjectionType.REWARD_BONUS,
            JournalIntent.INCOME_RECOGNITION,
            TaxTreatmentCode.ORDINARY_INCOME,
        ),
        "expense": (
            EconomicKind.CASH_EXPENSE,
            ProjectionType.EXPENSE_NON_TAXABLE,
            JournalIntent.EXPENSE_RECOGNITION,
            TaxTreatmentCode.NON_TAXABLE_EXPENSE,
        ),
        "swap": (
            EconomicKind.ASSET_SWAP,
            ProjectionType.SWAP_NON_TAXABLE,
            JournalIntent.ASSET_EXCHANGE,
            TaxTreatmentCode.NON_TAXABLE_ASSET_MIGRATION,
        ),
        "staking_reward": (
            EconomicKind.STAKING_REWARD,
            ProjectionType.STAKING,
            JournalIntent.INCOME_RECOGNITION,
            TaxTreatmentCode.STAKING_INCOME,
        ),
        "derivatives_profit": (
            EconomicKind.DERIVATIVE_REALIZED_PROFIT,
            ProjectionType.DERIVATIVES_FUTURES_PROFIT,
            JournalIntent.INCOME_RECOGNITION,
            TaxTreatmentCode.DERIVATIVE_REALIZED_GAIN,
        ),
        "derivatives_loss": (
            EconomicKind.DERIVATIVE_REALIZED_LOSS,
            ProjectionType.DERIVATIVES_FUTURES_LOSS,
            JournalIntent.EXPENSE_RECOGNITION,
            TaxTreatmentCode.DERIVATIVE_REALIZED_LOSS,
        ),
    }
    economic_kind, projection_type, journal_intent, tax_treatment_code = mapping[category]
    return classification(
        economic_kind=economic_kind,
        projection_type=projection_type,
        journal_intent=journal_intent,
        tax_treatment_code=tax_treatment_code,
    )
