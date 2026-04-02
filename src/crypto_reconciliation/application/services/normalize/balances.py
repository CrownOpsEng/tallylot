"""Application-owned balance derivation from normalized transactions."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from crypto_reconciliation.domain.models import BalanceSnapshot
from crypto_reconciliation.domain.models.transactions import NormalizedTransaction
from crypto_reconciliation.domain.types import AssetSymbol, SourceId


def derive_balance_snapshots(
    transactions: tuple[NormalizedTransaction, ...],
) -> tuple[BalanceSnapshot, ...]:
    balances: dict[tuple[str, str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    latest_timestamp: datetime | None = None
    for transaction in transactions:
        latest_timestamp = (
            transaction.timestamp if latest_timestamp is None else max(latest_timestamp, transaction.timestamp)
        )
        if transaction.asset_in is not None and transaction.amount_in is not None:
            _apply_balance_delta(
                balances,
                key=(
                    str(transaction.source),
                    transaction.account,
                    transaction.wallet,
                    str(transaction.asset_in),
                ),
                quantity=transaction.amount_in,
            )
        if transaction.asset_out is not None and transaction.amount_out is not None:
            _apply_balance_delta(
                balances,
                key=(
                    str(transaction.source),
                    transaction.account,
                    transaction.wallet,
                    str(transaction.asset_out),
                ),
                quantity=-transaction.amount_out,
            )
        if transaction.fee_asset is not None and transaction.fee_amount is not None:
            _apply_balance_delta(
                balances,
                key=(
                    str(transaction.source),
                    transaction.account,
                    transaction.wallet,
                    str(transaction.fee_asset),
                ),
                quantity=-transaction.fee_amount,
            )
    as_of = latest_timestamp if latest_timestamp is not None else datetime.now(UTC)
    return tuple(
        BalanceSnapshot(
            source=SourceId(source),
            account=account,
            wallet=wallet,
            asset=AssetSymbol(asset),
            quantity=quantity,
            as_of=as_of,
        )
        for (source, account, wallet, asset), quantity in sorted(balances.items())
    )


def _apply_balance_delta(
    balances: dict[tuple[str, str, str, str], Decimal],
    *,
    key: tuple[str, str, str, str],
    quantity: Decimal,
) -> None:
    balances[key] += quantity
