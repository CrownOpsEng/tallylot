"""Structured CSV translation helpers."""

from __future__ import annotations

from crypto_reconciliation.adapters.support.drafts import (
    ActivityClassification,
    EconomicActivityDraft,
    EconomicLegDraft,
    classification,
    economic_leg,
    fee_leg,
)
from crypto_reconciliation.domain.issues import NormalizationReviewRecord
from crypto_reconciliation.domain.value_objects import parse_decimal, parse_timestamp
from crypto_reconciliation.ports.source_profiles import SourceProfile

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
    fee_amount, fee_amount_review = validator.normalize_outbound_amount(index, "fee_amount", row["fee_amount"])
    reviews = tuple(review for review in (amount_out_review, fee_amount_review) if review is not None)
    account = row["account"].strip()
    wallet = row["wallet"].strip()
    legs: list[EconomicLegDraft] = []
    if row["asset_in"] and (amount_in := parse_decimal(row["amount_in"])) is not None:
        legs.append(economic_leg(direction="in", asset=row["asset_in"], amount=amount_in))
    if row["asset_out"] and amount_out is not None:
        legs.append(economic_leg(direction="out", asset=row["asset_out"], amount=amount_out))
    fee_legs = (
        (fee_leg(asset=row["fee_asset"], amount=fee_amount),) if row["fee_asset"] and fee_amount is not None else ()
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
        fee_legs=fee_legs,
    ), reviews


def classification_for_category(category: StructuredCategory) -> ActivityClassification:
    mapping: dict[str, tuple[str, str, str, str]] = {
        "trade": ("spot_trade", "Trade", "asset_exchange", "capital_exchange"),
        "deposit": ("asset_deposit", "Deposit", "funding_inflow", "non_taxable_transfer_in"),
        "withdrawal": ("asset_withdrawal", "Withdrawal", "funding_outflow", "non_taxable_transfer_out"),
        "interest_income": ("interest_income", "Interest Income", "income_recognition", "ordinary_income"),
        "reward": ("platform_reward", "Reward / Bonus", "income_recognition", "ordinary_income"),
        "expense": ("cash_expense", "Expense (non taxable)", "expense_recognition", "non_taxable_expense"),
        "swap": ("asset_swap", "Swap (non taxable)", "asset_exchange", "non_taxable_asset_migration"),
        "staking_reward": ("staking_reward", "Staking", "income_recognition", "staking_income"),
        "derivatives_profit": (
            "derivative_realized_profit",
            "Derivatives / Futures Profit",
            "income_recognition",
            "derivative_realized_gain",
        ),
        "derivatives_loss": (
            "derivative_realized_loss",
            "Derivatives / Futures Loss",
            "expense_recognition",
            "derivative_realized_loss",
        ),
    }
    economic_kind, projection_type, journal_intent, tax_treatment_code = mapping[category]
    return classification(
        economic_kind=economic_kind,
        projection_type=projection_type,
        journal_intent=journal_intent,
        tax_treatment_code=tax_treatment_code,
    )
