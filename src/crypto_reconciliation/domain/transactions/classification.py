"""Provider-neutral layered classification enums."""

from __future__ import annotations

from enum import StrEnum
from typing import TypeVar


class EconomicKind(StrEnum):
    ASSET_CONVERSION = "asset_conversion"
    ASSET_DEPOSIT = "asset_deposit"
    ASSET_MIGRATION = "asset_migration"
    ASSET_SWAP = "asset_swap"
    ASSET_WITHDRAWAL = "asset_withdrawal"
    CASH_EXPENSE = "cash_expense"
    CASH_WITHDRAWAL = "cash_withdrawal"
    CHAIN_TRANSFER_IN = "chain_transfer_in"
    DERIVATIVE_REALIZED_LOSS = "derivative_realized_loss"
    DERIVATIVE_REALIZED_PROFIT = "derivative_realized_profit"
    FIAT_DEPOSIT = "fiat_deposit"
    INTEREST_INCOME = "interest_income"
    P2P_TRADE = "p2p_trade"
    PLATFORM_REWARD = "platform_reward"
    SPOT_TRADE = "spot_trade"
    STAKING_REWARD = "staking_reward"
    STAKING_TRANSFER_IN = "staking_transfer_in"
    STAKING_TRANSFER_OUT = "staking_transfer_out"


class ProjectionType(StrEnum):
    DEPOSIT = "Deposit"
    DERIVATIVES_FUTURES_LOSS = "Derivatives / Futures Loss"
    DERIVATIVES_FUTURES_PROFIT = "Derivatives / Futures Profit"
    EXPENSE_NON_TAXABLE = "Expense (non taxable)"
    INTEREST_INCOME = "Interest Income"
    REWARD_BONUS = "Reward / Bonus"
    STAKING = "Staking"
    SWAP_NON_TAXABLE = "Swap (non taxable)"
    TRADE = "Trade"
    WITHDRAWAL = "Withdrawal"


class JournalIntent(StrEnum):
    ASSET_EXCHANGE = "asset_exchange"
    EXPENSE_RECOGNITION = "expense_recognition"
    FUNDING_INFLOW = "funding_inflow"
    FUNDING_OUTFLOW = "funding_outflow"
    INCOME_RECOGNITION = "income_recognition"


class TaxTreatmentCode(StrEnum):
    CAPITAL_EXCHANGE = "capital_exchange"
    DERIVATIVE_REALIZED_GAIN = "derivative_realized_gain"
    DERIVATIVE_REALIZED_LOSS = "derivative_realized_loss"
    NON_TAXABLE_ASSET_MIGRATION = "non_taxable_asset_migration"
    NON_TAXABLE_EXPENSE = "non_taxable_expense"
    NON_TAXABLE_TRANSFER_IN = "non_taxable_transfer_in"
    NON_TAXABLE_TRANSFER_OUT = "non_taxable_transfer_out"
    ORDINARY_INCOME = "ordinary_income"
    STAKING_INCOME = "staking_income"


EnumT = TypeVar("EnumT", bound=StrEnum)


def _parse_optional_enum(enum_type: type[EnumT], value: str) -> EnumT | None:
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return enum_type(stripped)
    except ValueError as error:
        raise ValueError(f"Unsupported {enum_type.__name__}: {stripped}") from error


def parse_economic_kind(value: str) -> EconomicKind | None:
    return _parse_optional_enum(EconomicKind, value)


def parse_projection_type(value: str) -> ProjectionType | None:
    return _parse_optional_enum(ProjectionType, value)


def parse_journal_intent(value: str) -> JournalIntent | None:
    return _parse_optional_enum(JournalIntent, value)


def parse_tax_treatment_code(value: str) -> TaxTreatmentCode | None:
    return _parse_optional_enum(TaxTreatmentCode, value)
