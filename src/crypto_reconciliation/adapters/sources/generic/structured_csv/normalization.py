"""Structured CSV normalization workflow."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.domain.models import (
    CanonicalBalance,
    CanonicalEvent,
    IssueRecord,
    NormalizationReviewRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, EventId, SourceId
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
                canonical_events=(),
                canonical_balances=(),
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
    events: list[CanonicalEvent] = []
    issues: list[IssueRecord] = []
    reviews: list[NormalizationReviewRecord] = []
    balances: dict[tuple[str, str, str], Decimal] = {}
    wallet_rows: dict[str, WalletInventoryRecord] = {}
    for index, row in enumerate(reader, start=2):
        row_issue = validator.validate_row(row, index)
        if row_issue is not None:
            issues.append(row_issue)
            continue
        event, row_reviews = _normalize_valid_row(
            profile,
            row,
            index,
            validator=validator,
        )
        events.append(event)
        reviews.extend(row_reviews)
        _apply_event_balance(balances, event)
        wallet_rows[_wallet_id(profile, event.account, event.wallet)] = _wallet_record(
            profile,
            raw_dir,
            event.account,
            event.wallet,
        )
    reviews.extend(_dataset_reviews(feedback, has_events=bool(events)))
    return NormalizationResult(
        canonical_events=tuple(events),
        canonical_balances=_balance_rows(profile, balances, events),
        issues=tuple(_issues_with_no_valid_rows(profile, feedback.adapter_id, issues, has_events=bool(events))),
        reviews=tuple(reviews),
        wallet_inventory=tuple(wallet_rows.values()),
    )


def _normalize_valid_row(
    profile: SourceProfile,
    row: dict[str, str],
    index: int,
    *,
    validator: StructuredCsvRowValidator,
) -> tuple[CanonicalEvent, tuple[NormalizationReviewRecord, ...]]:
    amount_out, amount_out_review = validator.canonicalize_outbound_amount(index, "amount_out", row["amount_out"])
    fee_amount, fee_amount_review = validator.canonicalize_outbound_amount(index, "fee_amount", row["fee_amount"])
    reviews = tuple(review for review in (amount_out_review, fee_amount_review) if review is not None)
    account = row["account"].strip()
    wallet = row["wallet"].strip()
    return CanonicalEvent(
        event_id=EventId(f"{profile.source}:{index}"),
        source=SourceId(str(profile.source)),
        adapter_id=AdapterId(validator.feedback.adapter_id),
        account=account,
        wallet=wallet,
        timestamp=parse_timestamp(row["timestamp"]),
        event_kind=row["event_kind"],
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
        render_type=row["event_kind"],
        render_exchange=account,
        render_comment=row["description"],
    ), reviews


def _apply_event_balance(
    balances: dict[tuple[str, str, str], Decimal],
    event: CanonicalEvent,
) -> None:
    if event.asset_in is not None and event.amount_in is not None:
        key = (event.account, event.wallet, str(event.asset_in))
        balances[key] = balances.get(key, Decimal("0")) + event.amount_in
    if event.asset_out is not None and event.amount_out is not None:
        key = (event.account, event.wallet, str(event.asset_out))
        balances[key] = balances.get(key, Decimal("0")) - event.amount_out
    if event.fee_asset is not None and event.fee_amount is not None:
        key = (event.account, event.wallet, str(event.fee_asset))
        balances[key] = balances.get(key, Decimal("0")) - event.fee_amount


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
    has_events: bool,
) -> tuple[NormalizationReviewRecord, ...]:
    if not has_events:
        return ()
    return (
        feedback.dataset_review(
            "timestamp_timezone_assumed_utc",
            (
                "Structured CSV timestamps are timezone-naive; normalization assigns UTC "
                "and those timestamps should be validated against the source system."
            ),
        ),
        feedback.dataset_review(
            "default_render_mapping",
            (
                "Structured CSV normalization defaults CoinTracking render fields to "
                "render_type<-event_kind, render_exchange<-account, and "
                "render_comment<-description; validate those mappings before import."
            ),
        ),
    )


def _balance_rows(
    profile: SourceProfile,
    balances: dict[tuple[str, str, str], Decimal],
    events: list[CanonicalEvent],
) -> tuple[CanonicalBalance, ...]:
    as_of = max(event.timestamp for event in events) if events else datetime.now(UTC)
    return tuple(
        CanonicalBalance(
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
    has_events: bool,
) -> list[IssueRecord]:
    if has_events:
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
