"""Structured CSV normalization workflow."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from crypto_reconciliation.domain.models import (
    BalanceSnapshot,
    IssueRecord,
    NormalizationReviewRecord,
    NormalizedTransaction,
    SourceProfile,
    TransactionCategory,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from crypto_reconciliation.domain.value_objects import parse_decimal, parse_timestamp
from crypto_reconciliation.ports.adapters import NormalizationResult

from .contracts import REQUIRED_HEADER, TRANSACTIONS_FILENAME
from .feedback import StructuredCsvFeedbackFactory
from .validation import StructuredCsvRowValidator


def normalize_structured_csv(
    profile: SourceProfile,
    raw_dir: Path,
    *,
    adapter_id: str,
) -> NormalizationResult:
    path = raw_dir / TRANSACTIONS_FILENAME
    feedback = StructuredCsvFeedbackFactory(profile=profile, adapter_id=adapter_id)
    validator = StructuredCsvRowValidator(feedback=feedback)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != REQUIRED_HEADER:
            return NormalizationResult(
                transactions=(),
                balances=(),
                issues=(
                    IssueRecord(
                        issue_id=f"{profile.source}:schema",
                        source=str(profile.source),
                        adapter_id=adapter_id,
                        severity="high",
                        kind="invalid_schema",
                        message="transactions.csv does not match the structured CSV schema.",
                        raw_file=TRANSACTIONS_FILENAME,
                    ),
                ),
                reviews=(),
                wallet_inventory=(),
            )
        return _normalized_result(profile, raw_dir, reader, feedback, validator)


def _normalized_result(
    profile: SourceProfile,
    raw_dir: Path,
    reader: csv.DictReader[str],
    feedback: StructuredCsvFeedbackFactory,
    validator: StructuredCsvRowValidator,
) -> NormalizationResult:
    transactions: list[NormalizedTransaction] = []
    issues: list[IssueRecord] = []
    reviews: list[NormalizationReviewRecord] = []
    balances: dict[tuple[str, str, str], Decimal] = {}
    wallet_rows: dict[str, WalletInventoryRecord] = {}
    for index, row in enumerate(reader, start=2):
        row_issue = validator.validate_row(row, index)
        if row_issue is not None:
            issues.append(row_issue)
            continue
        transaction, row_reviews = _normalize_valid_row(
            profile,
            row,
            index,
            validator=validator,
        )
        transactions.append(transaction)
        reviews.extend(row_reviews)
        _apply_transaction_balance(balances, transaction)
        wallet_rows[_wallet_id(profile, transaction.account, transaction.wallet)] = _wallet_record(
            profile,
            raw_dir,
            transaction.account,
            transaction.wallet,
        )
    reviews.extend(_dataset_reviews(feedback, has_transactions=bool(transactions)))
    return NormalizationResult(
        transactions=tuple(transactions),
        balances=_balance_rows(profile, balances, transactions),
        issues=tuple(
            _issues_with_no_valid_rows(
                profile,
                feedback.adapter_id,
                issues,
                has_transactions=bool(transactions),
            )
        ),
        reviews=tuple(reviews),
        wallet_inventory=tuple(wallet_rows.values()),
    )


def _normalize_valid_row(
    profile: SourceProfile,
    row: dict[str, str],
    index: int,
    *,
    validator: StructuredCsvRowValidator,
) -> tuple[NormalizedTransaction, tuple[NormalizationReviewRecord, ...]]:
    amount_out, amount_out_review = validator.normalize_outbound_amount(index, "amount_out", row["amount_out"])
    fee_amount, fee_amount_review = validator.normalize_outbound_amount(index, "fee_amount", row["fee_amount"])
    reviews = tuple(review for review in (amount_out_review, fee_amount_review) if review is not None)
    account = row["account"].strip()
    wallet = row["wallet"].strip()
    return NormalizedTransaction(
        transaction_id=TransactionId(f"{profile.source}:{index}"),
        source=SourceId(str(profile.source)),
        adapter_id=AdapterId(validator.feedback.adapter_id),
        account=account,
        wallet=wallet,
        timestamp=parse_timestamp(row["timestamp"]),
        category=cast(TransactionCategory, row["category"]),
        description=row["description"],
        asset_in=AssetSymbol(row["asset_in"]) if row["asset_in"] else None,
        amount_in=parse_decimal(row["amount_in"]),
        asset_out=AssetSymbol(row["asset_out"]) if row["asset_out"] else None,
        amount_out=amount_out,
        fee_asset=AssetSymbol(row["fee_asset"]) if row["fee_asset"] else None,
        fee_amount=fee_amount,
        tx_hash=row["tx_hash"] or None,
        raw_file=TRANSACTIONS_FILENAME,
        raw_row_ref=str(index),
    ), reviews


def _apply_transaction_balance(
    balances: dict[tuple[str, str, str], Decimal],
    transaction: NormalizedTransaction,
) -> None:
    if transaction.asset_in is not None and transaction.amount_in is not None:
        key = (transaction.account, transaction.wallet, str(transaction.asset_in))
        balances[key] = balances.get(key, Decimal("0")) + transaction.amount_in
    if transaction.asset_out is not None and transaction.amount_out is not None:
        key = (transaction.account, transaction.wallet, str(transaction.asset_out))
        balances[key] = balances.get(key, Decimal("0")) - transaction.amount_out
    if transaction.fee_asset is not None and transaction.fee_amount is not None:
        key = (transaction.account, transaction.wallet, str(transaction.fee_asset))
        balances[key] = balances.get(key, Decimal("0")) - transaction.fee_amount


def _wallet_id(profile: SourceProfile, account: str, wallet: str) -> str:
    return f"{profile.source}:{account}:{wallet}"


def _wallet_record(
    profile: SourceProfile,
    raw_dir: Path,
    account: str,
    wallet: str,
) -> WalletInventoryRecord:
    return WalletInventoryRecord(
        source=str(profile.source),
        capture_path=str(raw_dir),
        wallet_id=_wallet_id(profile, account, wallet),
        normalized_identifier=f"{account}:{wallet}",
        display_identifier=f"{account}:{wallet}",
        network_scope="",
        controller=account,
        account_label=wallet,
        evidence_kind="normalized_transactions",
        confidence="high",
        account=account,
        wallet=wallet,
        evidence_path=TRANSACTIONS_FILENAME,
        identifier_kind="account_wallet",
        identifier_value=f"{account}:{wallet}",
    )


def _dataset_reviews(
    feedback: StructuredCsvFeedbackFactory,
    *,
    has_transactions: bool,
) -> tuple[NormalizationReviewRecord, ...]:
    if not has_transactions:
        return ()
    return (
        feedback.dataset_review(
            "timestamp_timezone_assumed_utc",
            (
                "Structured CSV timestamps are timezone-naive; normalization assigns UTC "
                "and those timestamps should be validated against the source system."
            ),
        ),
    )


def _balance_rows(
    profile: SourceProfile,
    balances: dict[tuple[str, str, str], Decimal],
    transactions: list[NormalizedTransaction],
) -> tuple[BalanceSnapshot, ...]:
    as_of = max(transaction.timestamp for transaction in transactions) if transactions else datetime.now(UTC)
    return tuple(
        BalanceSnapshot(
            source=SourceId(str(profile.source)),
            account=account,
            wallet=wallet,
            asset=AssetSymbol(asset),
            quantity=quantity,
            as_of=as_of,
        )
        for (account, wallet, asset), quantity in sorted(balances.items())
    )


def _issues_with_no_valid_rows(
    profile: SourceProfile,
    adapter_id: str,
    issues: list[IssueRecord],
    *,
    has_transactions: bool,
) -> list[IssueRecord]:
    if has_transactions:
        return issues
    return [
        *issues,
        IssueRecord(
            issue_id=f"{profile.source}:no_valid_rows",
            source=str(profile.source),
            adapter_id=adapter_id,
            severity="high",
            kind="no_valid_rows",
            message="No valid rows were available for normalization.",
            raw_file=TRANSACTIONS_FILENAME,
        ),
    ]
