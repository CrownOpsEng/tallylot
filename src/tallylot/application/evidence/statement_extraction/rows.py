"""Statement document row formatting helpers."""

from __future__ import annotations

from tallylot.domain.value_objects import format_decimal, format_temporal_value
from tallylot.ports.evidence import StatementDocumentBalanceRow


def statement_row_to_pdf_balance_row(
    row: StatementDocumentBalanceRow,
) -> dict[str, str]:
    return {
        "source": row.source,
        "account": row.account,
        "wallet": row.wallet,
        "balance_kind": row.balance_kind,
        "asset": row.asset,
        "quantity": format_decimal(row.quantity),
        "staked_quantity": row.staked_quantity,
        "value_amount": row.value_amount,
        "value_currency": row.value_currency,
        "price_amount": row.price_amount,
        "price_currency": row.price_currency,
        "as_of": row_context_timestamp(row),
        "pdf_file": row.pdf_file,
        "notes": row.notes,
    }


def row_context_timestamp(row: StatementDocumentBalanceRow) -> str:
    if row.as_of_at is None:
        return row.as_of_text
    return format_temporal_value(
        row.as_of_at,
        precision=row.as_of_precision,
        label="statement evidence as_of",
    )
