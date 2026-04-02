"""Boundary parsers for persisted records."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from crypto_reconciliation.domain.models import NormalizedTransaction, TransactionCategory
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from crypto_reconciliation.domain.value_objects import parse_decimal
from crypto_reconciliation.ports.artifacts import ArtifactStorePort


def load_transactions(path: Path, artifacts: ArtifactStorePort) -> tuple[NormalizedTransaction, ...]:
    rows = artifacts.read_rows(path)
    transactions: list[NormalizedTransaction] = []
    for row in rows:
        transactions.append(
            NormalizedTransaction(
                transaction_id=TransactionId(row["transaction_id"]),
                source=SourceId(row["source"]),
                adapter_id=AdapterId(row["adapter_id"]),
                account=row["account"],
                wallet=row["wallet"],
                timestamp=_parse_utc_timestamp(row["timestamp"]),
                category=cast(TransactionCategory, row["category"]),
                economic_kind=row.get("economic_kind", ""),
                projection_type=row.get("projection_type", ""),
                journal_intent=row.get("journal_intent", ""),
                tax_treatment_code=row.get("tax_treatment_code", ""),
                provider_operation_key=row.get("provider_operation_key", ""),
                group_key=row.get("group_key", ""),
                description=row["description"],
                asset_in=AssetSymbol(row["asset_in"]) if row["asset_in"] else None,
                amount_in=parse_decimal(row["amount_in"]),
                asset_out=AssetSymbol(row["asset_out"]) if row["asset_out"] else None,
                amount_out=parse_decimal(row["amount_out"]),
                fee_asset=AssetSymbol(row["fee_asset"]) if row["fee_asset"] else None,
                fee_amount=parse_decimal(row["fee_amount"]),
                tx_hash=row["tx_hash"] or None,
                raw_file=row["raw_file"],
                raw_row_ref=row["raw_row_ref"],
                confidence=row["confidence"],
                status=row["status"],
            )
        )
    return tuple(transactions)


def _parse_utc_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
