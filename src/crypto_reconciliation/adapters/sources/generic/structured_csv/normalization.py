"""Structured CSV normalization workflow."""

from __future__ import annotations

import csv
from pathlib import Path

from crypto_reconciliation.adapters.support.drafts import (
    EconomicActivityDraft,
    translation_batch_from_drafts,
)
from crypto_reconciliation.adapters.support.issues import IssueSpec, issue_record
from crypto_reconciliation.domain.issues import IssueRecord, NormalizationReviewRecord
from crypto_reconciliation.ports.evidence import WalletInventoryRecord
from crypto_reconciliation.ports.source_profiles import SourceProfile
from crypto_reconciliation.ports.source_translation import SourceTranslationBatch

from .contracts import REQUIRED_HEADER, TRANSACTIONS_FILENAME
from .feedback import StructuredCsvFeedbackFactory
from .translation import translate_row
from .validation import StructuredCsvRowValidator


def translate_structured_csv(
    profile: SourceProfile,
    raw_dir: Path,
    *,
    adapter_id: str,
) -> SourceTranslationBatch:
    path = raw_dir / TRANSACTIONS_FILENAME
    feedback = StructuredCsvFeedbackFactory(profile=profile, adapter_id=adapter_id)
    validator = StructuredCsvRowValidator(feedback=feedback)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != REQUIRED_HEADER:
            return translation_batch_from_drafts(
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
) -> SourceTranslationBatch:
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
    return translation_batch_from_drafts(
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
    return translate_row(profile, row, index, validator=validator)


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
