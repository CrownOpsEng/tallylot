"""Structured CSV normalization workflow."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import cast

from crypto_reconciliation.adapters.support.drafts import (
    ActivityClassification,
    EconomicActivityDraft,
    EconomicLegDraft,
    classification,
    economic_leg,
    fee_leg,
    normalization_result_from_drafts,
)
from crypto_reconciliation.adapters.support.issues import IssueSpec, issue_record
from crypto_reconciliation.domain.models import (
    IssueRecord,
    NormalizationReviewRecord,
    SourceProfile,
    TransactionCategory,
    WalletInventoryRecord,
)
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
            return normalization_result_from_drafts(
                issues=(
                    issue_record(
                        IssueSpec(
                            issue_id=f"{profile.source}:schema",
                            source=str(profile.source),
                            adapter_id=adapter_id,
                            severity="high",
                            kind="invalid_schema",
                            message="transactions.csv does not match the structured CSV schema.",
                            raw_file=TRANSACTIONS_FILENAME,
                        )
                    ),
                ),
            )
        return _normalized_result(profile, raw_dir, reader, feedback, validator)


def _normalized_result(
    profile: SourceProfile,
    raw_dir: Path,
    reader: csv.DictReader[str],
    feedback: StructuredCsvFeedbackFactory,
    validator: StructuredCsvRowValidator,
) -> NormalizationResult:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    reviews: list[NormalizationReviewRecord] = []
    wallet_rows: dict[str, WalletInventoryRecord] = {}
    for index, row in enumerate(reader, start=2):
        row_issue = validator.validate_row(row, index)
        if row_issue is not None:
            issues.append(row_issue)
            continue
        draft, row_reviews = _normalize_valid_row(
            profile,
            row,
            index,
            validator=validator,
        )
        drafts.append(draft)
        reviews.extend(row_reviews)
        wallet_rows[_wallet_id(profile, row["account"].strip(), row["wallet"].strip())] = _wallet_record(
            profile,
            raw_dir,
            row["account"].strip(),
            row["wallet"].strip(),
        )
    reviews.extend(_dataset_reviews(feedback, has_transactions=bool(drafts)))
    return normalization_result_from_drafts(
        drafts,
        issues=_issues_with_no_valid_rows(
            profile,
            feedback.adapter_id,
            issues,
            has_transactions=bool(drafts),
        ),
        reviews=reviews,
        wallet_inventory=wallet_rows.values(),
    )


def _normalize_valid_row(
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
    category = cast(TransactionCategory, row["category"])
    return EconomicActivityDraft(
        activity_id=f"{profile.source}:{index}",
        source=str(profile.source),
        adapter_id=validator.feedback.adapter_id,
        account=account,
        wallet=wallet,
        timestamp=parse_timestamp(row["timestamp"]),
        classification=_classification_for_category(category),
        description=row["description"],
        raw_file=TRANSACTIONS_FILENAME,
        raw_row_ref=str(index),
        tx_hash=row["tx_hash"] or "",
        provider_operation_key=f"structured_csv:{category}",
        legs=tuple(legs),
        fee_legs=fee_legs,
    ), reviews


def _classification_for_category(category: TransactionCategory) -> ActivityClassification:
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
        normalized_category=category,
        economic_kind=economic_kind,
        projection_type=projection_type,
        journal_intent=journal_intent,
        tax_treatment_code=tax_treatment_code,
    )


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
        issue_record(
            IssueSpec(
                issue_id=f"{profile.source}:no_valid_rows",
                source=str(profile.source),
                adapter_id=adapter_id,
                severity="high",
                kind="no_valid_rows",
                message="No valid rows were available for normalization.",
                raw_file=TRANSACTIONS_FILENAME,
            )
        ),
    ]
