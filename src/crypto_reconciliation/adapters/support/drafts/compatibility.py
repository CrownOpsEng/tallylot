"""Bridge-only compatibility mapping for normalized transactions."""

from __future__ import annotations

from crypto_reconciliation.domain.models.transactions import TransactionCategory
from crypto_reconciliation.domain.transactions import JournalIntent, ProjectionType, TaxTreatmentCode

from .models import ActivityClassification

_PROJECTION_CATEGORY_MAP: dict[ProjectionType, TransactionCategory] = {
    ProjectionType.DEPOSIT: "deposit",
    ProjectionType.DERIVATIVES_FUTURES_LOSS: "derivatives_loss",
    ProjectionType.DERIVATIVES_FUTURES_PROFIT: "derivatives_profit",
    ProjectionType.EXPENSE_NON_TAXABLE: "expense",
    ProjectionType.INTEREST_INCOME: "interest_income",
    ProjectionType.REWARD_BONUS: "reward",
    ProjectionType.STAKING: "staking_reward",
    ProjectionType.SWAP_NON_TAXABLE: "swap",
    ProjectionType.TRADE: "trade",
    ProjectionType.WITHDRAWAL: "withdrawal",
}

_JOURNAL_CATEGORY_MAP: dict[JournalIntent, TransactionCategory] = {
    JournalIntent.FUNDING_INFLOW: "deposit",
    JournalIntent.FUNDING_OUTFLOW: "withdrawal",
}

_TAX_CATEGORY_MAP: dict[TaxTreatmentCode, TransactionCategory] = {
    TaxTreatmentCode.CAPITAL_EXCHANGE: "trade",
    TaxTreatmentCode.DERIVATIVE_REALIZED_GAIN: "derivatives_profit",
    TaxTreatmentCode.DERIVATIVE_REALIZED_LOSS: "derivatives_loss",
    TaxTreatmentCode.NON_TAXABLE_ASSET_MIGRATION: "swap",
    TaxTreatmentCode.NON_TAXABLE_EXPENSE: "expense",
    TaxTreatmentCode.ORDINARY_INCOME: "interest_income",
    TaxTreatmentCode.STAKING_INCOME: "staking_reward",
}


def compatibility_category_for_classification(classification: ActivityClassification) -> TransactionCategory:
    projection_type = classification.projection_type
    if projection_type is not None:
        return _PROJECTION_CATEGORY_MAP[projection_type]

    journal_category = _JOURNAL_CATEGORY_MAP.get(classification.journal_intent)
    if journal_category is not None:
        return journal_category

    tax_category = _TAX_CATEGORY_MAP.get(classification.tax_treatment_code)
    if tax_category is not None:
        return tax_category

    raise ValueError("activity classification is missing compatibility category metadata")
