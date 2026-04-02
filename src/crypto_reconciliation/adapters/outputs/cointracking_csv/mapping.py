"""CoinTracking-specific transaction type mapping."""

from __future__ import annotations

from crypto_reconciliation.domain.models import TransactionCategory

COINTRACKING_TYPE_BY_CATEGORY: dict[TransactionCategory, str] = {
    "trade": "Trade",
    "deposit": "Deposit",
    "withdrawal": "Withdrawal",
    "interest_income": "Interest Income",
    "reward": "Reward / Bonus",
    "expense": "Expense (non taxable)",
    "swap": "Swap (non taxable)",
    "staking_reward": "Staking",
    "derivatives_profit": "Derivatives / Futures Profit",
    "derivatives_loss": "Derivatives / Futures Loss",
}


def cointracking_type_for(category: TransactionCategory) -> str:
    return COINTRACKING_TYPE_BY_CATEGORY[category]
